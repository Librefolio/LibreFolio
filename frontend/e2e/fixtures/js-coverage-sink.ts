/**
 * One Playwright worker's JS coverage, summed as its tests finish.
 *
 * The `jsCoverage` fixture (`./playwright.ts`) hands every test's slice of
 * `window.__coverage__` to the worker's sink, which merges it into one istanbul
 * `CoverageMap` and writes that map to one file per worker:
 * `coverage-js/e2e-raw/worker-<parallelIndex>-<pid>.json`. The report
 * (`scripts/js-coverage-report.js`) reads that directory exactly as it read the
 * one-file-per-test directory before: same format, same merge.
 *
 * ### Why the sum equals what the report computed from per-test files
 *
 * The merge is istanbul-lib-coverage's own `CoverageMap.merge` — the call the
 * report makes. For one file and one build, every slice carries the same
 * statement, function and branch maps, so the merge adds the hit counts
 * location by location. Addition is associative, so summing in the worker and
 * then summing the workers gives the counts the report used to get by summing
 * every test. The slices are stored raw (absolute paths, `inputSourceMap`
 * kept): filtering, re-keying and the walk back through the sourcemaps stay in
 * the report, applied once to the sum.
 *
 * ### Why holding the sum in memory no longer kills the worker
 *
 * The 8 GB accumulator of the V8 era kept every payload: memory grew with the
 * number of tests. An istanbul map does not. `FileCoverage.merge` *replaces* the
 * hit counts and maps of a file, it never appends a payload; the bulk of a
 * slice — the `inputSourceMap` with the sources inside, most of the ~17 MB a
 * test produces — is kept once per source file, from the first slice that
 * loaded it, and every later copy is dropped with the slice. The map is bounded
 * by the number of modules in the build, not by the number of tests: about one
 * slice's size for the worker's whole life.
 *
 * ### How often the file is written
 *
 * Every `FLUSH_EVERY_TESTS` tests that brought counters, and at worker teardown.
 * A write costs the same whenever it happens (the file is the size of the map,
 * not of the slices since the last write), so the only question is how much a
 * worker may lose. Playwright tears a worker down normally after a failed test
 * (it sends `__stop__`, the worker fixtures' teardown runs, the file is
 * written), and after its last test. Only a worker killed outright — out of
 * memory, or force-killed by Playwright five minutes after a stop it ignored —
 * skips the teardown; it then loses at most the tests since the last write,
 * fewer than `FLUSH_EVERY_TESTS`. A count rather than a clock: a worker that
 * collects nothing has nothing to lose, and a test-count bound needs no timer
 * running beside the tests.
 *
 * Every write goes to `<name>.json.tmp` and is renamed over the file. The
 * report skips a file it cannot parse without a word, so a write torn by a kill
 * would silently replace the last good sum with nothing; with the rename the
 * file is either the old sum or the new one. The `.tmp` suffix also keeps a
 * half-written file out of both readers (`*.json`).
 *
 * ### Why a new worker absorbs the files of dead ones
 *
 * The runner splits a category into Playwright runs of a few specs under JS
 * coverage, and Playwright replaces a worker after every failed test: a full run
 * starts a hundred or more worker processes, and one file each would be a
 * hundred copies of the build's sourcemaps. So a worker, when it starts, merges
 * the files of the *dead* workers that held its `parallelIndex` before it, and
 * deletes them once its own file — which now contains them — has been written.
 * A full run then leaves about one file per parallel slot.
 *
 * Playwright never runs two live workers on one `parallelIndex` (it waits for
 * the old one to exit before starting the next), and the runner never runs two
 * Playwright invocations in one lane. The sink does not rely on either: a file
 * whose pid is still alive is left alone, whoever owns it. The one remaining
 * window — a worker killed between renaming its file and deleting the absorbed
 * ones — counts those tests' hits twice, which changes hit counts in the HTML
 * but not one covered/total figure (a statement hit twice is as covered as one
 * hit once). Nothing is ever lost to it.
 */
import {createRequire} from 'node:module';
import {mkdir, readdir, readFile, rename, rm, writeFile} from 'node:fs/promises';
import {join} from 'node:path';

/** Tests with counters between two writes of the worker file. See «How often the file is written». */
const FLUSH_EVERY_TESTS = 20;

/** The slice of `window.__coverage__` the fixture reads: istanbul file coverage, keyed by path. */
export type CoveragePayload = Record<string, unknown>;

/** The part of istanbul-lib-coverage used here. The package ships no types, and none is installed. */
type CoverageMap = {merge(data: CoveragePayload | CoverageMap): void; files(): string[]; toJSON(): unknown};
type IstanbulLibCoverage = {createCoverageMap(data?: CoveragePayload): CoverageMap};

// The same library, from the same `node_modules`, as `js-coverage-report.js`.
const libCoverage = createRequire(import.meta.url)('istanbul-lib-coverage') as IstanbulLibCoverage;

const WORKER_FILE = /^worker-(\d+)-(\d+)\.json(\.tmp)?$/;

/** Is `pid` a running process? `EPERM` means alive but not ours: still alive. */
function isAlive(pid: number): boolean {
    try {
        process.kill(pid, 0);
        return true;
    } catch (e) {
        return (e as NodeJS.ErrnoException).code === 'EPERM';
    }
}

/** Keep only what is file coverage, as the report does: an entry without a statement map is not one. */
function fileCoverageOnly(payload: CoveragePayload): CoveragePayload {
    const kept: CoveragePayload = {};
    for (const [key, value] of Object.entries(payload)) {
        if (value && typeof value === 'object' && (value as {statementMap?: unknown}).statementMap) kept[key] = value;
    }
    return kept;
}

export class WorkerCoverageSink {
    readonly dir: string;
    readonly parallelIndex: number;
    readonly pid: number;
    readonly flushEvery: number;
    readonly file: string;
    private readonly map = libCoverage.createCoverageMap({});
    /** Files of dead predecessors merged into `map`, deleted after the next write. */
    private absorbed: string[] = [];
    private sinceFlush = 0;
    private dirty = false;

    // Plain fields rather than parameter properties: Node can then load this file as it is (type
    // stripping), without Playwright's transpiler — handy to check the merge from a throwaway script.
    constructor(dir: string, parallelIndex: number, pid: number = process.pid, flushEvery: number = FLUSH_EVERY_TESTS) {
        this.dir = dir;
        this.parallelIndex = parallelIndex;
        this.pid = pid;
        this.flushEvery = flushEvery;
        this.file = join(dir, `worker-${parallelIndex}-${pid}.json`);
    }

    /**
     * Merge the files left by dead workers of the same `parallelIndex`; drop their torn `.tmp` files.
     * Returns how many files were merged. They stay on disk until the next `flush()` has written a
     * file that contains them.
     */
    async absorbDeadPredecessors(): Promise<number> {
        let names: string[];
        try {
            names = await readdir(this.dir);
        } catch {
            return 0; // No directory yet: nobody came before.
        }
        let merged = 0;
        for (const name of names) {
            const m = WORKER_FILE.exec(name);
            if (!m || Number(m[1]) !== this.parallelIndex) continue;
            const pid = Number(m[2]);
            if (pid === this.pid || isAlive(pid)) continue;
            const path = join(this.dir, name);
            if (m[3]) {
                // A write its worker never finished: the previous whole sum is still in the `.json`.
                await rm(path, {force: true});
                continue;
            }
            try {
                this.mergeEach(fileCoverageOnly(JSON.parse(await readFile(path, 'utf-8')) as CoveragePayload));
            } catch (e) {
                // Leave it where it is: the report reads (or skips) it as it would any other file.
                console.warn(`[coverage-js] could not absorb ${name}:`, e);
                continue;
            }
            this.absorbed.push(path);
            this.dirty = true;
            merged += 1;
        }
        return merged;
    }

    /**
     * Merge entry by entry. `CoverageMap.merge` validates every entry before it adds any, so one malformed
     * module would drop the whole slice; the per-test file kept the rest, and so does this.
     */
    private mergeEach(slice: CoveragePayload): number {
        let merged = 0;
        for (const [key, value] of Object.entries(slice)) {
            try {
                this.map.merge({[key]: value});
                merged += 1;
            } catch (e) {
                console.warn(`[coverage-js] skipped malformed coverage for ${key}:`, e);
            }
        }
        return merged;
    }

    /**
     * Add one test's counters, one payload per page of its context: every page is summed into the worker's map,
     * so a module two pages loaded counts the hits of both. Write the worker file every `flushEvery` tests.
     */
    async add(...payloads: CoveragePayload[]): Promise<void> {
        let merged = 0;
        for (const payload of payloads) merged += this.mergeEach(fileCoverageOnly(payload));
        if (merged === 0) return;
        this.dirty = true;
        this.sinceFlush += 1;
        if (this.sinceFlush >= this.flushEvery) await this.flush();
    }

    /** Write the whole sum atomically, then delete the predecessors' files it now contains. */
    async flush(): Promise<void> {
        if (!this.dirty) return;
        await mkdir(this.dir, {recursive: true});
        const tmp = `${this.file}.tmp`;
        await writeFile(tmp, JSON.stringify(this.map.toJSON()));
        await rename(tmp, this.file);
        this.dirty = false;
        this.sinceFlush = 0;
        // Forget a predecessor only once its file is gone: a deletion that failed is retried at the next
        // write, rather than leaving its tests counted twice for the rest of the run.
        const results = await Promise.allSettled(this.absorbed.map((path) => rm(path, {force: true})));
        this.absorbed = this.absorbed.filter((_, i) => results[i].status === 'rejected');
    }
}
