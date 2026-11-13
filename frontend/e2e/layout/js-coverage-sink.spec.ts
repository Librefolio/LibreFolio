/**
 * The worker's JS coverage sink (`e2e/fixtures/js-coverage-sink.ts`) and the stopwatches of the E2E coverage collection
 * (project 71, block 3, C2: «a lighter collection»).
 *
 * Why. Every test of a run under JS coverage pays, after it ends, to read `window.__coverage__` from each page (about 17 MB
 * of JSON on the instrumented build), merge it into the worker's sum and, every twenty tests, write that sum. Nothing said
 * what each part costs, so nothing could say whether a change made the collection lighter. Step 3.6 only measures: with
 * `LF_COV_TIMING=1` the fixture writes one line per test into `coverage-js/timing/worker-<parallelIndex>-<pid>.jsonl`, and
 * `scripts/js-coverage-probe.mjs timing` (step 3.7) reads them. Without the flag nothing is measured and nothing is
 * stringified.
 *
 * What this file holds, all pure: no page, no server, no login. The fake `__coverage__` it hands the sink uses keys outside
 * `src/` (`/fake/…`), so that under `--coverage js`, where the real fixture collects this spec's own pages too, the report
 * drops them (`keep()` of `scripts/js-coverage-report.js` keeps `src/` only).
 *
 *   - JCS-01a…d (step 3.6) the stopwatches: with a write every two tests, the second `add()` carries a write time above
 *     zero, the first none; the record of a test has exactly the six fields of the plan; the log appends one JSON line per
 *     test to the worker's own file; only `LF_COV_TIMING=1` turns them on; the payload's size is counted in bytes.
 *   - JCS-02…07 (step 3.7) the sink sums counters as arrays: the fixed parts of a file (its maps, `inputSourceMap`, `hash`)
 *     are kept once, the hit counts as arrays added index by index, and the file it writes is, read back with
 *     `createCoverageMap`, the one istanbul's own `CoverageMap.merge` of the same full objects gives — «the old path», the
 *     reference every case is held to, duplicate positions (which istanbul folds from its second merge on) included. A
 *     page that already sent a file sends only its counters (`addLight`, step 3.8 reads them in the page); a file of a
 *     different build goes through istanbul's merge, by position.
 *   - JCP-01 `scripts/js-coverage-probe.mjs timing` reads the stopwatch lines: per field n, mean, p50, p95, total, max.
 */
import {spawnSync} from 'node:child_process';
import {mkdir, mkdtemp, readFile, rm, writeFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {expect, test} from '../fixtures/playwright';
import {WorkerCoverageSink, counterArrays, payloadBytes, timingEnabled, timingRecord, TimingLog, type CoveragePayload} from '../fixtures/js-coverage-sink';

/** istanbul-lib-coverage, from the same `node_modules` the sink and the report load it from: the reference of every case. */
const libCoverage = createRequire(import.meta.url)('istanbul-lib-coverage') as {
    createCoverageMap(data?: CoveragePayload): {merge(data: CoveragePayload): void; toJSON(): CoveragePayload};
};
const PROBE = fileURLToPath(new URL('../../scripts/js-coverage-probe.mjs', import.meta.url));

/** One file's istanbul coverage with a single statement hit `hits` times: the smallest payload the sink accepts. */
function fakeFile(path: string, hits: number): CoveragePayload {
    return {
        [path]: {
            path,
            statementMap: {'0': {start: {line: 1, column: 0}, end: {line: 1, column: 5}}},
            fnMap: {},
            branchMap: {},
            s: {'0': hits},
            f: {},
            b: {},
        },
    };
}

const SIX_FIELDS = ['evaluate_ms', 'heap_mb', 'merge_ms', 'payload_bytes', 'rss_mb', 'flush_ms'].sort();

test.describe('JCS, the stopwatches of the E2E coverage collection', () => {
    let dir: string;

    test.beforeEach(async () => {
        dir = await mkdtemp(join(tmpdir(), 'lf-js-coverage-sink-'));
    });

    test.afterEach(async () => {
        await rm(dir, {recursive: true, force: true});
    });

    test('JCS-01a the sink says what a merge and a write cost, and a record has the six fields', async () => {
        const sink = new WorkerCoverageSink(join(dir, 'e2e-raw'), 0, process.pid, 2);

        const first = await sink.add(fakeFile('/fake/a.ts', 1));
        const second = await sink.add(fakeFile('/fake/a.ts', 2));

        expect(first.flush_ms, 'the first test of two did not reach a write').toBe(0);
        expect(first.merge_ms).toBeGreaterThanOrEqual(0);
        expect(second.flush_ms, 'the second test brought the write').toBeGreaterThan(0);
        expect(second.merge_ms).toBeGreaterThanOrEqual(0);

        const record = timingRecord(12.5, 4096, second);
        expect(Object.keys(record).sort()).toEqual(SIX_FIELDS);
        expect(record).toMatchObject({evaluate_ms: 12.5, payload_bytes: 4096, merge_ms: second.merge_ms, flush_ms: second.flush_ms});
        expect(record.rss_mb).toBeGreaterThan(0);
        expect(record.heap_mb).toBeGreaterThan(0);
    });

    test('JCS-01b a payload with no file coverage costs nothing and writes nothing', async () => {
        const sink = new WorkerCoverageSink(join(dir, 'e2e-raw'), 0, process.pid, 1);

        const timing = await sink.add({'/fake/not-coverage': {}});

        expect(timing).toEqual({merge_ms: 0, flush_ms: 0});
    });

    test('JCS-01c the log appends one JSON line per test to the worker’s own file', async () => {
        const log = new TimingLog(join(dir, 'timing'), 3, 4242);
        const one = timingRecord(1, 10, {merge_ms: 2, flush_ms: 0});
        const two = timingRecord(3, 30, {merge_ms: 4, flush_ms: 5});

        await log.append(one);
        await log.append(two);

        expect(log.file.endsWith(join('timing', 'worker-3-4242.jsonl'))).toBe(true);
        const lines = (await readFile(log.file, 'utf-8')).trimEnd().split('\n');
        expect(lines.map((line) => JSON.parse(line))).toEqual([one, two]);
    });

    test('JCS-01d only LF_COV_TIMING=1 turns the stopwatches on, and the size is counted in bytes', () => {
        expect(timingEnabled({LF_COV_TIMING: '1'})).toBe(true);
        for (const env of [{}, {LF_COV_TIMING: ''}, {LF_COV_TIMING: '0'}, {LF_COV_TIMING: 'true'}]) {
            expect(timingEnabled(env), JSON.stringify(env)).toBe(false);
        }
        // 'é' is one character and two bytes: the size on the wire is the bytes.
        expect(payloadBytes([{a: 'é'}])).toBe(Buffer.byteLength('[{"a":"é"}]'));
        expect(payloadBytes([])).toBe(2);
    });
});

type Loc = {start: {line: number; column: number}; end: {line: number; column: number}};
const loc = (line: number, from: number, to: number): Loc => ({start: {line, column: from}, end: {line, column: to}});

/**
 * One instrumented module as the build's `window.__coverage__` carries it: three statements, one function, one `if` with
 * two paths, its `hash`, a stand-in `inputSourceMap` (the bulk of a real slice). `duplicate` gives the third statement the
 * position of the second, as two statements istanbul cannot tell apart; `bT` adds the logic-truthiness counters.
 */
function module(path: string, hash: string, hits: {s: number[]; f: number[]; b: number[][]; bT?: number[][]}, duplicate = false): CoveragePayload {
    const third = duplicate ? loc(2, 0, 9) : loc(3, 0, 9);
    const value: Record<string, unknown> = {
        path,
        statementMap: {'0': loc(1, 0, 9), '1': loc(2, 0, 9), '2': third},
        fnMap: {'0': {name: 'f', decl: loc(1, 9, 10), loc: loc(1, 0, 20), line: 1}},
        branchMap: {'0': {type: 'if', loc: loc(2, 0, 30), locations: [loc(2, 0, 30), loc(2, 0, 30)], line: 2}},
        s: {'0': hits.s[0], '1': hits.s[1], '2': hits.s[2]},
        f: {'0': hits.f[0]},
        b: {'0': hits.b[0]},
        inputSourceMap: {version: 3, sources: [path], mappings: 'AAAA', sourcesContent: ['x'.repeat(64)]},
        _coverageSchema: '1a1c01bbd47fc00a2c39e90264f33305004495a9',
        hash,
    };
    if (hits.bT) value.bT = {'0': hits.bT[0]};
    return {[path]: value};
}

/** The old path: every full payload merged entry by entry into one istanbul map, as the sink did until step 3.7. */
function oldPath(...payloads: CoveragePayload[]): CoveragePayload {
    const map = libCoverage.createCoverageMap({});
    for (const payload of payloads) for (const [key, value] of Object.entries(structuredClone(payload))) map.merge({[key]: value});
    return JSON.parse(JSON.stringify(map.toJSON())) as CoveragePayload;
}

/** What the sink wrote, read back as the report reads it. */
async function written(sink: WorkerCoverageSink): Promise<CoveragePayload> {
    await sink.flush();
    return JSON.parse(JSON.stringify(libCoverage.createCoverageMap(JSON.parse(await readFile(sink.file, 'utf-8'))).toJSON())) as CoveragePayload;
}

/** A page's light slice of one module: its counters as arrays, nothing else (the shape `readCoverageInPage` returns, step 3.8). */
function light(payload: CoveragePayload): CoveragePayload {
    return Object.fromEntries(Object.entries(payload).map(([key, value]) => [key, counterArrays(value as Record<string, unknown>)]));
}

test.describe('JCS, the counter-based sink (step 3.7): the same file as istanbul’s own merge', () => {
    let dir: string;

    test.beforeEach(async () => {
        dir = await mkdtemp(join(tmpdir(), 'lf-js-coverage-sink-'));
    });

    test.afterEach(async () => {
        await rm(dir, {recursive: true, force: true});
    });

    test('JCS-02 counters summed index by index equal CoverageMap.merge of the full objects', async () => {
        const a1 = module('/fake/a.ts', 'ha', {s: [1, 0, 2], f: [1], b: [[1, 0]]});
        const a2 = module('/fake/a.ts', 'ha', {s: [0, 3, 1], f: [2], b: [[0, 4]]});
        const b1 = module('/fake/b.ts', 'hb', {s: [5, 5, 5], f: [0], b: [[2, 2]]});
        const sink = new WorkerCoverageSink(join(dir, 'e2e-raw'), 0, process.pid, 100);

        await sink.add(structuredClone(a1), structuredClone(b1));
        await sink.add(structuredClone(a2));

        expect(await written(sink)).toEqual(oldPath(a1, b1, a2));
    });

    test('JCS-03 a file seen in full, then as counters only, sums to the same file', async () => {
        const first = module('/fake/a.ts', 'ha', {s: [1, 0, 0], f: [1], b: [[1, 0]]});
        const second = module('/fake/a.ts', 'ha', {s: [0, 2, 0], f: [0], b: [[0, 3]]});
        const third = module('/fake/a.ts', 'ha', {s: [4, 0, 1], f: [1], b: [[1, 1]]});
        const sink = new WorkerCoverageSink(join(dir, 'e2e-raw'), 0, process.pid, 100);

        await sink.addLight(structuredClone(first));
        expect(sink.knownHashes(), 'once seen in full, a page may send its counters alone').toEqual({'/fake/a.ts': 'ha'});
        await sink.addLight(light(second), light(third));

        expect(await written(sink)).toEqual(oldPath(first, second, third));
    });

    test('JCS-04 a file of a different build is merged by istanbul, by position, and is no longer offered for counters', async () => {
        const old = module('/fake/a.ts', 'h-old', {s: [1, 1, 0], f: [1], b: [[1, 0]]});
        const rebuilt = module('/fake/a.ts', 'h-new', {s: [0, 0, 7], f: [0], b: [[0, 2]]});
        (rebuilt['/fake/a.ts'] as {statementMap: Record<string, Loc>}).statementMap['2'] = loc(4, 0, 9);
        const sink = new WorkerCoverageSink(join(dir, 'e2e-raw'), 0, process.pid, 100);

        await sink.addLight(structuredClone(old));
        await sink.addLight(structuredClone(rebuilt));

        expect(await written(sink)).toEqual(oldPath(old, rebuilt));
        expect(sink.knownHashes(), 'two builds of one file: the page must send it in full').toEqual({});
        const before = await written(sink);
        await sink.addLight(light(old));
        expect(await written(sink), 'counters for a build the sink no longer holds as such are not added').toEqual(before);
    });

    test('JCS-05 a full predecessor file is absorbed, and a page’s first full slice makes the file known again', async () => {
        const predecessor = oldPath(module('/fake/a.ts', 'ha', {s: [1, 1, 1], f: [1], b: [[1, 1]]}), module('/fake/a.ts', 'ha', {s: [1, 0, 0], f: [0], b: [[0, 1]]}));
        const raw = join(dir, 'e2e-raw');
        await mkdir(raw, {recursive: true});
        const deadPid = 999_999_999; // no such process
        await writeFile(join(raw, `worker-0-${deadPid}.json`), JSON.stringify(predecessor));
        const page1 = module('/fake/a.ts', 'ha', {s: [2, 0, 0], f: [1], b: [[3, 0]]});
        const page2 = module('/fake/a.ts', 'ha', {s: [0, 0, 5], f: [0], b: [[0, 0]]});
        const sink = new WorkerCoverageSink(raw, 0, process.pid, 100);

        expect(await sink.absorbDeadPredecessors()).toBe(1);
        expect(sink.knownHashes(), 'a file read from disk is not the page’s layout: not offered until a page sends it').toEqual({});
        await sink.addLight(structuredClone(page1));
        await sink.addLight(light(page2));

        expect(await written(sink)).toEqual(oldPath(predecessor, page1, page2));
    });

    test('JCS-06 the written file equals the old path, duplicate positions and files seen once included', async () => {
        const dupe1 = module('/fake/dupe.ts', 'hd', {s: [1, 2, 3], f: [1], b: [[1, 0]]}, true);
        const dupe2 = module('/fake/dupe.ts', 'hd', {s: [4, 5, 6], f: [0], b: [[0, 1]]}, true);
        const dupe3 = module('/fake/dupe.ts', 'hd', {s: [7, 8, 9], f: [2], b: [[2, 2]]}, true);
        const once = module('/fake/once.ts', 'ho', {s: [1, 2, 3], f: [1], b: [[1, 1]]}, true);
        const sink = new WorkerCoverageSink(join(dir, 'e2e-raw'), 0, process.pid, 100);

        await sink.addLight(structuredClone(dupe1), structuredClone(once));
        await sink.addLight(light(dupe2));
        await sink.addLight(structuredClone(dupe3));

        const expected = oldPath(dupe1, once, dupe2, dupe3);
        expect(Object.keys((expected['/fake/dupe.ts'] as {s: object}).s), 'istanbul folded the two statements at one position').toHaveLength(2);
        expect(Object.keys((expected['/fake/once.ts'] as {s: object}).s), 'a file seen once is written as it came').toHaveLength(3);
        expect(await written(sink)).toEqual(expected);
    });

    test('JCS-06b two hundred seeded sequences, full and counters interleaved, equal the old path', async () => {
        // A small deterministic generator (mulberry32): the same 200 cases on every run, every machine.
        let seed = 71;
        const random = () => {
            seed = (seed + 0x6d2b79f5) | 0;
            let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
            t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
            return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
        };
        const int = (n: number) => Math.floor(random() * n);
        /**
         * A module of 1–6 statements, 1–3 functions, 1–3 branches of 2–3 paths; some items share a position. With `bT` the
         * branches never do: istanbul's own merge of `bT` reads the branch map it has just folded and throws on a duplicate
         * (`file-coverage.js`, `merge`), and the build never carries `bT` (no `reportLogic` in `vite.config.ts`).
         */
        const layoutFor = (path: string, distinctBranches: boolean) => {
            const statements = 1 + int(6);
            const functions = 1 + int(3);
            const branches = 1 + int(3);
            const paths = Array.from({length: branches}, () => 2 + int(2));
            const line = (i: number, of: number, distinct = false) => (!distinct && int(4) === 0 && i > 0 ? i : i + 1) + of; // one in four reuses the line before
            return {path, statements: Array.from({length: statements}, (_, i) => line(i, 0)), functions: Array.from({length: functions}, (_, i) => line(i, 100)), branches: Array.from({length: branches}, (_, i) => line(i, 200, distinctBranches)), paths};
        };
        const slice = (l: ReturnType<typeof layoutFor>, hash: string, withBT: boolean): CoveragePayload => {
            const value: Record<string, unknown> = {
                path: l.path,
                statementMap: Object.fromEntries(l.statements.map((at, i) => [String(i), loc(at, 0, 9)])),
                fnMap: Object.fromEntries(l.functions.map((at, i) => [String(i), {name: `f${i}`, decl: loc(at, 0, 1), loc: loc(at, 0, 9), line: at}])),
                branchMap: Object.fromEntries(l.branches.map((at, i) => [String(i), {type: 'if', loc: loc(at, 0, 9), locations: Array.from({length: l.paths[i]}, () => loc(at, 0, 9)), line: at}])),
                s: Object.fromEntries(l.statements.map((_, i) => [String(i), int(3)])),
                f: Object.fromEntries(l.functions.map((_, i) => [String(i), int(3)])),
                b: Object.fromEntries(l.paths.map((n, i) => [String(i), Array.from({length: n}, () => int(3))])),
                inputSourceMap: {version: 3, sources: [l.path], mappings: 'AAAA'},
                hash,
            };
            if (withBT) value.bT = Object.fromEntries(l.paths.map((n, i) => [String(i), Array.from({length: n}, () => int(3))]));
            return {[l.path]: value};
        };

        for (let run = 0; run < 200; run++) {
            const withBT = int(2) === 0;
            const layouts = Array.from({length: 1 + int(3)}, (_, i) => layoutFor(`/fake/m${i}.ts`, withBT));
            const sink = new WorkerCoverageSink(join(dir, `e2e-raw-${run}`), 0, process.pid, 1_000);
            const sent: CoveragePayload[] = [];
            for (let step = 0, steps = 1 + int(6); step < steps; step++) {
                const l = layouts[int(layouts.length)];
                const full = slice(l, `h-${l.path}`, withBT);
                sent.push(full);
                const known = sink.knownHashes()[l.path] !== undefined;
                await (known && int(3) > 0 ? sink.addLight(light(full)) : sink.addLight(structuredClone(full)));
            }
            expect(await written(sink), `case ${run}`).toEqual(oldPath(...sent));
        }
    });

    test('JCS-07 the logic-truthiness counters (bT) are summed like the branches', async () => {
        const first = module('/fake/a.ts', 'ha', {s: [1, 0, 0], f: [1], b: [[1, 0]], bT: [[1, 0]]});
        const second = module('/fake/a.ts', 'ha', {s: [0, 1, 0], f: [0], b: [[0, 2]], bT: [[0, 2]]});
        const sink = new WorkerCoverageSink(join(dir, 'e2e-raw'), 0, process.pid, 100);

        await sink.addLight(structuredClone(first));
        await sink.addLight(light(second));

        const result = await written(sink);
        expect(result).toEqual(oldPath(first, second));
        expect((result['/fake/a.ts'] as {bT: Record<string, number[]>}).bT['0']).toEqual([1, 2]);
    });

    test('JCP-01 the timing reader prints n, mean, p50, p95, total and max per field, and counts what it cannot read', async () => {
        const timing = join(dir, 'timing');
        await mkdir(timing, {recursive: true});
        const line = (evaluate: number, flush: number) => JSON.stringify(timingRecord(evaluate, evaluate * 10, {merge_ms: 1, flush_ms: flush}));
        await writeFile(join(timing, 'worker-0-1.jsonl'), [line(1, 0), line(2, 0), 'torn {'].join('\n') + '\n');
        await writeFile(join(timing, 'worker-1-2.jsonl'), [line(3, 0), line(10, 40)].join('\n') + '\n');

        const run = spawnSync(process.execPath, [PROBE, 'timing', timing, '--json'], {encoding: 'utf-8'});

        expect(run.status, run.stderr).toBe(0);
        const out = JSON.parse(run.stdout) as {files: number; tests: number; skipped: number; fields: Record<string, Record<string, number>>};
        expect([out.files, out.tests, out.skipped]).toEqual([2, 4, 1]);
        expect(out.fields.evaluate_ms).toEqual({n: 4, mean: 4, p50: 2, p95: 10, total: 16, max: 10});
        expect(out.fields.flush_ms.total).toBe(40);
        expect(Object.keys(out.fields).sort()).toEqual(SIX_FIELDS);
    });
});
