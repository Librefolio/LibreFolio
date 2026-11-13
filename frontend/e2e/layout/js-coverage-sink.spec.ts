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
 *   - JCS-01 the sink says what a merge and a write cost: with a write every two tests, the second `add()` carries a write
 *     time above zero, the first none; the record of a test has exactly the six fields of the plan.
 *   - JCS-02 the log appends one JSON line per test, to the worker's own file, and creates its directory.
 *   - JCS-03 the stopwatches are opt-in: only `LF_COV_TIMING=1` turns them on; the payload's size is counted in bytes, not
 *     characters.
 */
import {mkdtemp, readFile, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {expect, test} from '../fixtures/playwright';
import {WorkerCoverageSink, payloadBytes, timingEnabled, timingRecord, TimingLog, type CoveragePayload} from '../fixtures/js-coverage-sink';

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

    test('JCS-01 the sink says what a merge and a write cost, and a record has the six fields', async () => {
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

    test('JCS-02 the log appends one JSON line per test to the worker’s own file', async () => {
        const log = new TimingLog(join(dir, 'timing'), 3, 4242);
        const one = timingRecord(1, 10, {merge_ms: 2, flush_ms: 0});
        const two = timingRecord(3, 30, {merge_ms: 4, flush_ms: 5});

        await log.append(one);
        await log.append(two);

        expect(log.file.endsWith(join('timing', 'worker-3-4242.jsonl'))).toBe(true);
        const lines = (await readFile(log.file, 'utf-8')).trimEnd().split('\n');
        expect(lines.map((line) => JSON.parse(line))).toEqual([one, two]);
    });

    test('JCS-03 only LF_COV_TIMING=1 turns the stopwatches on, and the size is counted in bytes', () => {
        expect(timingEnabled({LF_COV_TIMING: '1'})).toBe(true);
        for (const env of [{}, {LF_COV_TIMING: ''}, {LF_COV_TIMING: '0'}, {LF_COV_TIMING: 'true'}]) {
            expect(timingEnabled(env), JSON.stringify(env)).toBe(false);
        }
        // 'é' is one character and two bytes: the size on the wire is the bytes.
        expect(payloadBytes([{a: 'é'}])).toBe(Buffer.byteLength('[{"a":"é"}]'));
        expect(payloadBytes([])).toBe(2);
    });
});
