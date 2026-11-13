/**
 * One Playwright worker's JS coverage, summed as its tests finish.
 *
 * The `jsCoverage` fixture (`./playwright.ts`) hands every test's slice of
 * `window.__coverage__` to the worker's sink, which sums it as istanbul's merge
 * would and writes the sum to one file per worker:
 * `coverage-js/e2e-raw/worker-<parallelIndex>-<pid>.json`. The report
 * (`scripts/js-coverage-report.js`) reads that directory exactly as it read the
 * one-file-per-test directory before: same format, same merge.
 *
 * ### How the sum is held: fixed parts once, counters as arrays (step 3.7)
 *
 * A file coverage is two things of very different sizes: its fixed parts — the statement, function and branch maps,
 * `inputSourceMap` with the sources inside (most of the ~17 MB a test produces), `hash`, `path` — identical in every slice
 * of one build, and its hit counters, a few numbers per statement. The sink keeps the fixed parts of each file once, from
 * the first slice that brought it, and the counters as arrays; a later slice adds its counters index by index. It rebuilds
 * full objects only when it writes, so the file on disk, and what the report reads, keep their format.
 *
 * ### Why the sum equals istanbul's own merge
 *
 * The reference is istanbul-lib-coverage's `CoverageMap.merge` — what this sink called until step 3.7, and what the report
 * still calls. Its `FileCoverage.merge` does not add by key: it keys every item by its position (`keyFromLoc`; a function by
 * its `loc`, a branch by its first location), so two items at one position are one item to it, the last one's counts
 * winning, and the keys come out renumbered from 0. It does that from a file's second slice on; a file seen once is kept as
 * it came. The sink replays exactly that: it computes the fold of a layout once (`foldOf`), applies it to a file at its
 * second slice, and adds every later slice through it. Addition is associative, so summing in the worker and then summing
 * the workers gives the counts the report would get from every slice. `js-coverage-sink.spec.ts` holds the sink to istanbul's
 * merge on the same slices, duplicate positions and two hundred seeded sequences included.
 *
 * ### Counters alone from a page, and the cases that go back to istanbul
 *
 * Once a page has sent a file in full, the sink knows that build's layout (`knownHashes()`): a later page sends only its
 * counters as arrays for it (`addLight`, the page side is step 3.8), which the sink places through the same fold. A file
 * read from a dead predecessor is a sum, not a page's layout: it is merged, but never offered for counters until a page
 * sends the file in full. A slice whose layout differs from the one held — another build of the file, an `all`
 * placeholder — goes through istanbul's merge itself, by position, and that file then takes full slices only.
 *
 * ### Why holding the sum in memory no longer kills the worker
 *
 * The 8 GB accumulator of the V8 era kept every payload: memory grew with the number of tests. This sum does not: it holds
 * each module's fixed parts once and one array of numbers per counter, bounded by the number of modules in the build, not
 * by the number of tests.
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
 * ### The stopwatches
 *
 * Under `LF_COV_TIMING=1` the fixture writes, per test, one line into `coverage-js/timing/worker-<i>-<pid>.jsonl` (`TimingLog`):
 * the page read, the size of what it returned, the merge and the write (`add()` and `flush()` return their own milliseconds) and
 * the worker's memory. Measure only: nothing here changes what is collected. See `scripts/js-coverage-probe.mjs timing`.
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
import {appendFile, mkdir, readdir, readFile, rename, rm, writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {performance} from 'node:perf_hooks';

/** Tests with counters between two writes of the worker file. See «How often the file is written». */
const FLUSH_EVERY_TESTS = 20;

/** The slice of `window.__coverage__` the fixture reads: istanbul file coverage, keyed by path. */
export type CoveragePayload = Record<string, unknown>;

/** What one `add()` cost, in milliseconds: summing the slices into the map, and the write it triggered (0 when it did not write). */
export type AddTiming = {merge_ms: number; flush_ms: number};

/** The line the fixture writes for one test under `LF_COV_TIMING=1`: what each part of its collection cost. */
export type TimingRecord = {evaluate_ms: number; payload_bytes: number; merge_ms: number; flush_ms: number; rss_mb: number; heap_mb: number};

const MB = 1024 * 1024;

/** Are the stopwatches on? Only `LF_COV_TIMING=1`: a flag that is not set costs the collection nothing, not even the size of the payload. */
export function timingEnabled(env: Record<string, string | undefined> = process.env): boolean {
    return env.LF_COV_TIMING === '1';
}

/** The size of what the page handed over, in bytes on the wire (UTF-8), as `JSON.stringify` writes it. Called only with the stopwatches on. */
export function payloadBytes(payloads: unknown): number {
    return Buffer.byteLength(JSON.stringify(payloads));
}

/** One test's record: the page read (`evaluateMs`), the size of what it returned, what the sink spent, and the worker's memory now. */
export function timingRecord(evaluateMs: number, bytes: number, added: AddTiming): TimingRecord {
    const memory = process.memoryUsage();
    return {evaluate_ms: evaluateMs, payload_bytes: bytes, merge_ms: added.merge_ms, flush_ms: added.flush_ms, rss_mb: memory.rss / MB, heap_mb: memory.heapUsed / MB};
}

/** One worker's timing file, `coverage-js/timing/worker-<parallelIndex>-<pid>.jsonl`: a JSON object per line, appended. */
export class TimingLog {
    readonly file: string;
    private readonly dir: string;

    constructor(dir: string, parallelIndex: number, pid: number = process.pid) {
        this.dir = dir;
        this.file = join(dir, `worker-${parallelIndex}-${pid}.jsonl`);
    }

    async append(record: TimingRecord): Promise<void> {
        await mkdir(this.dir, {recursive: true});
        await appendFile(this.file, JSON.stringify(record) + '\n');
    }
}

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

/** The three counters of a file coverage and the map each one is keyed by. */
type Counter = 's' | 'f' | 'b';
const COUNTERS: readonly Counter[] = ['s', 'f', 'b'];
const MAP_OF = {s: 'statementMap', f: 'fnMap', b: 'branchMap'} as const;

type Loc = {start: {line: number; column: number}; end: {line: number; column: number}};
type Hit = number | number[];

/** istanbul's position keys (`file-coverage.js`, `keyFromLoc` and the two props of `merge`): a statement by its range, a
 * function by its `loc`, a branch by its first location. Two items with one key are one item to istanbul's merge. */
const keyFromLoc = ({start, end}: Loc): string => `${start.line}|${start.column}|${end.line}|${end.column}`;
const ITEM_KEY: Record<Counter, (item: never) => string> = {
    s: (item: Loc) => keyFromLoc(item),
    f: (item: {loc: Loc}) => keyFromLoc(item.loc),
    b: (item: {locations: Loc[]}) => keyFromLoc(item.locations[0]),
};

/** A page's counters of one file: its `hash` and every counter as an array, in the page's own key order. */
export type LightEntry = {hash: string; s: number[]; f: number[]; b: number[][]; bT?: number[][]};

/** The values of a counter object, in its key order (integer keys: ascending, on both sides of the page). */
const valuesOf = <T>(counter: Record<string, T>): T[] => Object.keys(counter).map((key) => counter[key]);
const copyHit = (hit: Hit): Hit => (Array.isArray(hit) ? [...hit] : hit);

/** The counters of a full file coverage as arrays: what a page sends for a file the sink already holds (step 3.8). */
export function counterArrays(file: Record<string, unknown>): LightEntry {
    const light: LightEntry = {
        hash: String(file.hash),
        s: valuesOf(file.s as Record<string, number>),
        f: valuesOf(file.f as Record<string, number>),
        b: valuesOf(file.b as Record<string, number[]>).map((hits) => [...hits]),
    };
    if (file.bT) light.bT = valuesOf(file.bT as Record<string, number[]>).map((hits) => [...hits]);
    return light;
}

/** Where each item of a file lands once istanbul has merged it (`mergeProp`): its slot, or −1 when a later item at the same
 * position replaces it (istanbul keys items by position, so the last one wins the slot the first one opened). */
type Fold = {plan: Record<Counter, number[]>; maps: Record<Counter, unknown[]>; keys: Record<Counter, string[]>};

function foldOf(file: Record<string, unknown>): Fold {
    const fold = {plan: {}, maps: {}, keys: {}} as Fold;
    for (const counter of COUNTERS) {
        const map = file[MAP_OF[counter]] as Record<string, never>;
        const hitKeys = Object.keys(file[counter] as object);
        const slot = new Map<string, number>();
        const owner = new Map<string, number>();
        const items: unknown[] = [];
        const positions = hitKeys.map((hitKey, i) => {
            const position = ITEM_KEY[counter](map[hitKey]);
            if (!slot.has(position)) slot.set(position, slot.size);
            owner.set(position, i);
            items[slot.get(position)!] = map[hitKey];
            return position;
        });
        fold.plan[counter] = positions.map((position, i) => (owner.get(position) === i ? slot.get(position)! : -1));
        fold.maps[counter] = items;
        fold.keys[counter] = [...slot.keys()];
    }
    return fold;
}

/** istanbul's `addHits`: two counts, or two branch arrays element by element, the length of the first. */
const addHit = (a: Hit, b: Hit): Hit => (Array.isArray(a) ? a.map((value, i) => (value || 0) + ((b as number[])[i] || 0)) : (a as number) + (b as number));

/**
 * One file the worker holds: its fixed parts once — the three maps, `inputSourceMap` (most of a slice's bytes), `hash`,
 * `path`, `_coverageSchema` — and its counters as arrays.
 */
type Held = {
    fixed: Record<string, unknown>;
    keys: Record<Counter | 'bT', string[]>;
    hits: {s: Hit[]; f: Hit[]; b: Hit[]; bT?: Hit[]};
    /** Merged at least once: istanbul's fold (one item per position, keys renumbered) has been applied. */
    folded: boolean;
    /** The layout of the page's own slices of this file (its build's `hash` and fold), known once a page sent it in full. */
    page?: {hash: string; plan: Record<Counter, number[]>; lengths: number[]};
    /** Two builds of the file were merged: only istanbul's merge, by position, can add to it any more. */
    mixed: boolean;
    /** The position keys of the folded layout, in slot order: what a full slice must match to be added by index. */
    positions?: Record<Counter, string[]>;
};

function held(value: Record<string, unknown>): Held {
    const {s, f, b, bT, ...fixed} = value as Record<string, Record<string, Hit>>;
    const hits: Held['hits'] = {s: valuesOf(s).map(copyHit), f: valuesOf(f).map(copyHit), b: valuesOf(b).map(copyHit)};
    const keys = {s: Object.keys(s), f: Object.keys(f), b: Object.keys(b), bT: bT ? Object.keys(bT) : []};
    if (bT) hits.bT = valuesOf(bT).map(copyHit);
    return {fixed, keys, hits, folded: false, mixed: false};
}

/** The file coverage of a held file, as istanbul holds it: the object the old sink wrote. */
function rebuilt(file: Held): Record<string, unknown> {
    const object = (keys: string[], hits: Hit[]) => Object.fromEntries(keys.map((key, i) => [key, copyHit(hits[i])]));
    const data: Record<string, unknown> = {...file.fixed, s: object(file.keys.s, file.hits.s), f: object(file.keys.f, file.hits.f), b: object(file.keys.b, file.hits.b)};
    if (file.hits.bT) data.bT = object(file.keys.bT, file.hits.bT);
    return data;
}

/** Apply istanbul's fold to a held file, as its first merge does: one item per position, slots renumbered from 0. */
function fold(file: Held): void {
    if (file.folded) return;
    const {plan, maps} = foldOf(rebuilt(file));
    for (const counter of COUNTERS) {
        const hits: Hit[] = [];
        file.hits[counter].forEach((hit, i) => {
            if (plan[counter][i] >= 0) hits[plan[counter][i]] = hit;
        });
        file.hits[counter] = hits;
        file.fixed[MAP_OF[counter]] = Object.fromEntries(maps[counter].map((item, j) => [String(j), item]));
        file.keys[counter] = hits.map((_, j) => String(j));
    }
    if (file.hits.bT) {
        const hits: Hit[] = [];
        file.hits.bT.forEach((hit, i) => {
            if (plan.b[i] >= 0) hits[plan.b[i]] = hit;
        });
        file.hits.bT = hits;
        file.keys.bT = hits.map((_, j) => String(j));
    }
    file.folded = true;
}

/** The position keys of a held file's folded layout, computed once per layout. */
function positionsOf(file: Held): Record<Counter, string[]> {
    fold(file);
    file.positions ??= foldOf(rebuilt(file)).keys;
    return file.positions;
}

/** Add a slice's counters, in its own layout, through its fold plan: what istanbul's merge adds for the same file. */
function addThrough(file: Held, plan: Record<Counter, number[]>, slice: {s: Hit[]; f: Hit[]; b: Hit[]; bT?: Hit[]}): void {
    for (const counter of COUNTERS) {
        slice[counter].forEach((hit, i) => {
            const j = plan[counter][i];
            if (j >= 0) file.hits[counter][j] = addHit(file.hits[counter][j], hit);
        });
    }
    // istanbul adds the truthiness counters only when both sides have them.
    if (file.hits.bT && slice.bT) {
        slice.bT.forEach((hit, i) => {
            const j = plan.b[i];
            if (j >= 0) file.hits.bT![j] = addHit(file.hits.bT![j], hit);
        });
    }
}

const lengthsOf = (slice: {s: unknown[]; f: unknown[]; b: unknown[]}): number[] => [slice.s.length, slice.f.length, slice.b.length];
const sameLengths = (a: number[], b: number[]): boolean => a.length === b.length && a.every((n, i) => n === b[i]);

export class WorkerCoverageSink {
    readonly dir: string;
    readonly parallelIndex: number;
    readonly pid: number;
    readonly flushEvery: number;
    readonly file: string;
    /** Every file the worker has seen, by key: fixed parts once, counters as arrays. */
    private readonly files = new Map<string, Held>();
    /** Files of dead predecessors merged into `files`, deleted after the next write. */
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

    /** `{key: hash}` of the files a page may send as counters alone: seen in full from a page, one build only. */
    knownHashes(): Record<string, string> {
        const known: Record<string, string> = {};
        for (const [key, file] of this.files) if (file.page && !file.mixed) known[key] = file.page.hash;
        return known;
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
                // A file read from disk is a sum, not a page's layout: it never makes its files known for counters.
                this.mergeEach(fileCoverageOnly(JSON.parse(await readFile(path, 'utf-8')) as CoveragePayload), false);
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

    /** One full file coverage into the sum: what istanbul's `CoverageMap.merge` would make of it. */
    private mergeFull(key: string, value: Record<string, unknown>, fromPage: boolean): void {
        const file = this.files.get(key);
        if (!file) {
            // istanbul keeps a file it has not seen as it came, unfolded: so does the sink.
            const fresh = held(value);
            if (fromPage && typeof value.hash === 'string') fresh.page = {hash: value.hash, plan: foldOf(value).plan, lengths: lengthsOf(fresh.hits)};
            this.files.set(key, fresh);
            return;
        }
        const incoming = foldOf(value);
        const sameLayout =
            !file.mixed &&
            value.all !== true &&
            file.fixed.all !== true &&
            COUNTERS.every((counter) => {
                const mine = positionsOf(file)[counter];
                return mine.length === incoming.keys[counter].length && mine.every((position, i) => position === incoming.keys[counter][i]);
            });
        if (!sameLayout) {
            this.mergeByIstanbul(key, file, value);
            return;
        }
        const slice = held(value).hits;
        addThrough(file, incoming.plan, slice);
        if (fromPage && !file.page && value.hash === file.fixed.hash) file.page = {hash: String(value.hash), plan: incoming.plan, lengths: lengthsOf(slice)};
    }

    /** A file whose layout differs (another build, a placeholder): istanbul's own merge, by position, and the sum read back. */
    private mergeByIstanbul(key: string, file: Held, value: Record<string, unknown>): void {
        const map = libCoverage.createCoverageMap({[key]: rebuilt(file)} as CoveragePayload);
        map.merge({[key]: value});
        // `toJSON()` hands back `FileCoverage` instances; their plain data is what the sink holds (a rare path: a round trip is fine).
        const merged = held((JSON.parse(JSON.stringify(map.toJSON())) as Record<string, Record<string, unknown>>)[key]);
        merged.folded = file.fixed.all !== true;
        merged.mixed = file.mixed || value.hash !== file.fixed.hash;
        if (!merged.mixed && file.page) merged.page = file.page;
        this.files.set(key, merged);
    }

    /** A page's counters of a file it already sent in full; false when the sink cannot place them (unknown file, another build). */
    private mergeLight(key: string, light: LightEntry): boolean {
        const file = this.files.get(key);
        if (!file?.page || file.mixed || light.hash !== file.page.hash || !sameLengths(lengthsOf(light), file.page.lengths)) return false;
        fold(file);
        addThrough(file, file.page.plan, light);
        return true;
    }

    /**
     * Merge entry by entry, so that one malformed module never drops the rest of the slice: an entry with a statement map is a
     * full file coverage, any other a page's counters (`LightEntry`).
     */
    private mergeEach(slice: CoveragePayload, fromPage: boolean): number {
        let merged = 0;
        for (const [key, value] of Object.entries(slice)) {
            try {
                const entry = value as Record<string, unknown>;
                if (entry && typeof entry === 'object' && entry.statementMap) {
                    this.mergeFull(key, entry, fromPage);
                } else if (!this.mergeLight(key, entry as unknown as LightEntry)) {
                    console.warn(`[coverage-js] counters for ${key} match no file the sink holds: skipped`);
                    continue;
                }
                merged += 1;
            } catch (e) {
                console.warn(`[coverage-js] skipped malformed coverage for ${key}:`, e);
            }
        }
        return merged;
    }

    /**
     * Add one test's slices in full, one payload per page of its context: every page is summed into the worker's sum,
     * so a module two pages loaded counts the hits of both. Write the worker file every `flushEvery` tests.
     * Returns what the merge and the write cost (two clock reads: the stopwatches' own cost is not worth a flag).
     */
    async add(...payloads: CoveragePayload[]): Promise<AddTiming> {
        return this.take(payloads.map(fileCoverageOnly));
    }

    /**
     * Add one test's slices as a page reads them (step 3.8): counters alone (`LightEntry`) for the files of `knownHashes()`,
     * the full file coverage for any other. Same sum, same file, as `add` of the full slices.
     */
    async addLight(...payloads: CoveragePayload[]): Promise<AddTiming> {
        return this.take(payloads);
    }

    private async take(payloads: CoveragePayload[]): Promise<AddTiming> {
        const start = performance.now();
        let merged = 0;
        for (const payload of payloads) merged += this.mergeEach(payload, true);
        const mergeMs = performance.now() - start;
        if (merged === 0) return {merge_ms: 0, flush_ms: 0};
        this.dirty = true;
        this.sinceFlush += 1;
        const flushMs = this.sinceFlush >= this.flushEvery ? await this.flush() : 0;
        return {merge_ms: mergeMs, flush_ms: flushMs};
    }

    /** Write the whole sum atomically, then delete the predecessors' files it now contains. Returns how long the write took, in milliseconds (0 when there was nothing to write). */
    async flush(): Promise<number> {
        if (!this.dirty) return 0;
        const start = performance.now();
        await mkdir(this.dir, {recursive: true});
        const tmp = `${this.file}.tmp`;
        const sum: Record<string, unknown> = {};
        for (const [key, file] of this.files) sum[key] = rebuilt(file);
        await writeFile(tmp, JSON.stringify(sum));
        await rename(tmp, this.file);
        this.dirty = false;
        this.sinceFlush = 0;
        // Forget a predecessor only once its file is gone: a deletion that failed is retried at the next
        // write, rather than leaving its tests counted twice for the rest of the run.
        const results = await Promise.allSettled(this.absorbed.map((path) => rm(path, {force: true})));
        this.absorbed = this.absorbed.filter((_, i) => results[i].status === 'rejected');
        return performance.now() - start;
    }
}
