/**
 * storageBarModel — the pure helper behind the storage bar of the Files page (lot FB-29, written red first against
 * `B6r-fb29-interface.md` §5).
 *
 * The backend measures (bytes, sums); the frontend only turns those bytes into the percentages of a bar. The rules under
 * test, in the order the contract states them:
 *   - `mode`: `limit` when `limit_mb` > 0 (whatever the volume says); otherwise `volume` when `volume_total_bytes` is
 *     known and > 0; otherwise `data`;
 *   - `totalBytes`: `limit_mb × 1048576` (limit), `volume_total_bytes` (volume), `data_bytes` (data);
 *   - `segments`, in this order: `database`, `uploads`, `brokerReports`, `backups`, `dataOther` (= `other_bytes`), and
 *     only in `volume` mode `disk` (= `max(0, volume_used − data_bytes)`, the files on the disk that are not
 *     LibreFolio's); each `{id, bytes, percent}` with `percent` = bytes / totalBytes × 100 rounded to 2 decimals; a segment
 *     of 0 bytes is left out; the percentages never add up to more than 100 (when they would, the LAST segment gives
 *     way);
 *   - `usedBytes` = the sum of the segments; `freeBytes` = `max(0, totalBytes − usedBytes)` in `limit` and 0 in `data`,
 *     `volume_free_bytes` in `volume`; `freePercent` the same share of the bar; `overLimit` = `mode === 'limit'` and
 *     `data_bytes > totalBytes`.
 *
 * The numbers are the test's own, chosen so that the expected percentages are exact (a quarter of the bar is 25) or sit
 * clear of a rounding tie. A zero total never divides by zero: no NaN or Infinity comes out.
 *
 * Red today: `./storageBar` does not exist; it is loaded inside each case so each one fails on its own.
 *
 * Node environment: nothing here touches the DOM.
 */
import {describe, expect, it} from 'vitest';
import type {InstanceStorage} from '$lib/features/backup/backupApi';

// A literal path would fail the whole file at transform time while the module is missing; a variable path fails each case alone.
const MODULES = {model: './storageBar'};
type Segment = {id: string; bytes: number; percent: number};
type Model = {mode: string; totalBytes: number; segments: Segment[]; usedBytes: number; freeBytes: number; freePercent: number; overLimit: boolean; limitPercent: number | null};
const modelOf = async (usage: InstanceStorage): Promise<Model> => {
    const module = await import(/* @vite-ignore */ MODULES.model);
    return module.storageBarModel(usage) as Model;
};

const MiB = 1024 * 1024;
const GiB = 1024 * MiB;

type Parts = {database?: number; uploads?: number; brokerReports?: number; backups?: number; other?: number};

/** A measurement. The data folder is the sum of its five parts unless `data_bytes` is given; no volume and no limit unless asked. */
function usage(parts: Parts = {}, extra: Partial<InstanceStorage> = {}): InstanceStorage {
    const database_bytes = parts.database ?? 0;
    const uploads_bytes = parts.uploads ?? 0;
    const broker_reports_bytes = parts.brokerReports ?? 0;
    const backups_bytes = parts.backups ?? 0;
    const other_bytes = parts.other ?? 0;
    return {
        database_bytes,
        uploads_bytes,
        broker_reports_bytes,
        backups_bytes,
        other_bytes,
        data_bytes: database_bytes + uploads_bytes + broker_reports_bytes + backups_bytes + other_bytes,
        volume_total_bytes: null,
        volume_used_bytes: null,
        volume_free_bytes: null,
        limit_mb: null,
        limit_locked: false,
        ...extra,
    } as InstanceStorage;
}

/** A disk of `total` bytes of which `used` are taken. */
const disk = (total: number, used: number): Partial<InstanceStorage> => ({volume_total_bytes: total, volume_used_bytes: used, volume_free_bytes: total - used});

/** The segments reduced to what the contract names (an implementation may carry more fields). */
const shape = (model: Model) => model.segments.map(({id, bytes, percent}) => ({id, bytes, percent}));
const ids = (model: Model) => model.segments.map((segment) => segment.id);
const sumOfPercents = (model: Model) => Math.round(model.segments.reduce((sum, segment) => sum + segment.percent, 0) * 100) / 100;

// =====================================================================================================================
describe('storageBarModel — which mode', () => {
    it('a limit above 0 is limit mode, even when the volume is known', async () => {
        const model = await modelOf(usage({database: 10 * MiB}, {limit_mb: 1024, ...disk(10 * GiB, 5 * GiB)}));

        expect(model.mode).toBe('limit');
        expect(model.totalBytes).toBe(1024 * MiB);
    });

    it('a limit that the environment pins is the limit all the same', async () => {
        const model = await modelOf(usage({database: 10 * MiB}, {limit_mb: 512, limit_locked: true}));

        expect(model.mode).toBe('limit');
        expect(model.totalBytes).toBe(512 * MiB);
    });

    it.each<[string, Partial<InstanceStorage>]>([
        ['no limit (null)', {limit_mb: null}],
        ['a limit of 0', {limit_mb: 0}],
        ['a limit of 0 that the environment pins', {limit_mb: 0, limit_locked: true}],
    ])('%s and a known volume: volume mode, the bar is the disk', async (_case, extra) => {
        const model = await modelOf(usage({database: 10 * MiB}, {...disk(10 * GiB, 5 * GiB), ...extra}));

        expect(model.mode).toBe('volume');
        expect(model.totalBytes).toBe(10 * GiB);
    });

    it.each<[string, Partial<InstanceStorage>]>([
        ['an unknown volume (all three None)', {volume_total_bytes: null, volume_used_bytes: null, volume_free_bytes: null}],
        ['a volume of 0 bytes', {volume_total_bytes: 0, volume_used_bytes: 0, volume_free_bytes: 0}],
    ])('no limit and %s: data mode, the bar is the data folder', async (_case, extra) => {
        const model = await modelOf(usage({database: 30 * MiB, uploads: 10 * MiB}, extra));

        expect(model.mode).toBe('data');
        expect(model.totalBytes).toBe(40 * MiB);
    });
});

// =====================================================================================================================
describe('storageBarModel — limit mode', () => {
    it('LibreFolio’s parts against the limit, in order; exact shares of the bar; the rest is free', async () => {
        // A 1 GiB limit; 960 MiB used: a quarter, an eighth, a sixteenth and half of the bar.
        const model = await modelOf(usage({database: 256 * MiB, uploads: 128 * MiB, brokerReports: 64 * MiB, backups: 512 * MiB}, {limit_mb: 1024}));

        expect(model.mode).toBe('limit');
        expect(model.totalBytes).toBe(GiB);
        expect(shape(model)).toEqual([
            {id: 'database', bytes: 256 * MiB, percent: 25},
            {id: 'uploads', bytes: 128 * MiB, percent: 12.5},
            {id: 'brokerReports', bytes: 64 * MiB, percent: 6.25},
            {id: 'backups', bytes: 512 * MiB, percent: 50},
        ]);
        expect(model.usedBytes).toBe(960 * MiB);
        expect(model.freeBytes).toBe(64 * MiB);
        expect(model.freePercent).toBe(6.25);
        expect(model.overLimit).toBe(false);
    });

    it('never draws the disk in limit mode, whatever the volume holds', async () => {
        const model = await modelOf(usage({database: 100 * MiB}, {limit_mb: 1024, ...disk(10 * GiB, 9 * GiB)}));

        expect(ids(model)).toEqual(['database']);
        expect(model.usedBytes).toBe(100 * MiB);
    });

    it('all five parts come out in the order database, uploads, brokerReports, backups, dataOther, each percent rounded to 2 decimals', async () => {
        // Against 1024 MiB: 100 → 9.765625, 50 → 4.8828125, 20 → 1.953125, 70 → 6.8359375, 10 → 0.9765625. No rounding tie.
        const model = await modelOf(usage({database: 100 * MiB, uploads: 50 * MiB, brokerReports: 20 * MiB, backups: 70 * MiB, other: 10 * MiB}, {limit_mb: 1024}));

        expect(ids(model)).toEqual(['database', 'uploads', 'brokerReports', 'backups', 'dataOther']);
        expect(model.segments.map((segment) => segment.percent)).toEqual([9.77, 4.88, 1.95, 6.84, 0.98]);
        expect(model.segments.map((segment) => segment.bytes)).toEqual([100 * MiB, 50 * MiB, 20 * MiB, 70 * MiB, 10 * MiB]);
        for (const segment of model.segments) expect(Math.round(segment.percent * 100) / 100, `${segment.id} has at most 2 decimals`).toBe(segment.percent);
        expect(model.usedBytes).toBe(250 * MiB);
        expect(model.freeBytes).toBe(774 * MiB);
        // The share of the free part: 75.5859… of the bar, however the rounding is taken.
        expect(Math.abs(model.freePercent - 75.5859375)).toBeLessThanOrEqual(0.01);
        expect(model.overLimit).toBe(false);
    });

    it('a part of 0 bytes is left out; the others keep their order', async () => {
        const model = await modelOf(usage({database: 256 * MiB, uploads: 0, brokerReports: 0, backups: 256 * MiB, other: 0}, {limit_mb: 1024}));

        expect(ids(model)).toEqual(['database', 'backups']);
        expect(model.segments.every((segment) => segment.bytes > 0)).toBe(true);
    });

    it('nothing stored: no segment at all, the whole bar is free', async () => {
        const model = await modelOf(usage({}, {limit_mb: 1024}));

        expect(model.segments).toEqual([]);
        expect(model.usedBytes).toBe(0);
        expect(model.freeBytes).toBe(GiB);
        expect(model.freePercent).toBe(100);
        expect(model.overLimit).toBe(false);
    });
});

// =====================================================================================================================
describe('storageBarModel — over the limit', () => {
    it('data above the limit: overLimit, nothing free, and every part keeps its share: the bar is the data, the limit a tick inside it (C9-4)', async () => {
        // 150 MiB in a 100 MiB limit: the bar is the 150 MiB, the limit at two thirds of it.
        const model = await modelOf(usage({database: 90 * MiB, backups: 60 * MiB}, {limit_mb: 100}));

        expect(model.mode).toBe('limit');
        expect(model.overLimit).toBe(true);
        expect(model.usedBytes).toBe(150 * MiB);
        expect(model.freeBytes).toBe(0);
        expect(model.freePercent).toBe(0);
        expect(ids(model)).toEqual(['database', 'backups']);
        expect(sumOfPercents(model)).toBe(100);
        expect(model.segments[0].percent).toBe(60);
        expect(model.segments[1].percent).toBe(40);
        expect(model.totalBytes, 'the bar is the data').toBe(150 * MiB);
        expect(model.limitPercent, 'the limit, at two thirds of the bar').toBeCloseTo(66.67, 2);
        expect(model.segments.map((segment) => segment.bytes)).toEqual([90 * MiB, 60 * MiB]);
    });

    it('data exactly at the limit is full, not over', async () => {
        const model = await modelOf(usage({database: 60 * MiB, backups: 40 * MiB}, {limit_mb: 100}));

        expect(model.overLimit).toBe(false);
        expect(model.freeBytes).toBe(0);
        expect(model.freePercent).toBe(0);
        expect(sumOfPercents(model)).toBe(100);
        expect(model.limitPercent, 'within the limit: no tick, the bar is the limit').toBeNull();
    });

    it('one byte above the limit is over', async () => {
        const model = await modelOf(usage({database: 100 * MiB, other: 1}, {limit_mb: 100}));

        expect(model.overLimit).toBe(true);
        expect(model.freeBytes).toBe(0);
        expect(sumOfPercents(model)).toBeLessThanOrEqual(100);
    });

    it.each<[string, Partial<InstanceStorage>]>([
        ['volume mode', disk(10 * GiB, 9 * GiB)],
        ['data mode', {}],
    ])('overLimit is a limit-mode flag only: %s with a lot of data is not over', async (_case, extra) => {
        const model = await modelOf(usage({database: 8 * GiB}, extra));

        expect(model.overLimit).toBe(false);
    });
});

// =====================================================================================================================
describe('storageBarModel — volume mode', () => {
    it('LibreFolio’s parts, then the rest of the disk, then free: the whole disk is the bar', async () => {
        // A 10 GiB disk, 6 GiB taken, 4 GiB free; LibreFolio's folder is 3584 MiB of the 6144 MiB taken.
        const model = await modelOf(usage({database: 1024 * MiB, uploads: 512 * MiB, backups: 2048 * MiB}, disk(10 * GiB, 6 * GiB)));

        expect(model.mode).toBe('volume');
        expect(model.totalBytes).toBe(10 * GiB);
        expect(shape(model)).toEqual([
            {id: 'database', bytes: 1024 * MiB, percent: 10},
            {id: 'uploads', bytes: 512 * MiB, percent: 5},
            {id: 'backups', bytes: 2048 * MiB, percent: 20},
            {id: 'disk', bytes: 2560 * MiB, percent: 25},
        ]);
        expect(model.usedBytes).toBe(6 * GiB);
        expect(model.freeBytes).toBe(4 * GiB);
        expect(model.freePercent).toBe(40);
        expect(model.overLimit).toBe(false);
    });

    it('the disk segment comes last, after all five parts', async () => {
        const model = await modelOf(usage({database: 1024 * MiB, uploads: 512 * MiB, brokerReports: 256 * MiB, backups: 2048 * MiB, other: 128 * MiB}, disk(100 * GiB, 50 * GiB)));

        expect(ids(model)).toEqual(['database', 'uploads', 'brokerReports', 'backups', 'dataOther', 'disk']);
        expect(model.freeBytes).toBe(50 * GiB);
        expect(sumOfPercents(model)).toBeLessThanOrEqual(100);
    });

    it('freeBytes is what the volume says is free, not total minus the drawn parts', async () => {
        // 10 GiB disk, 6 GiB taken: but the volume reports 3 GiB free (reserved blocks): that is what is shown.
        const model = await modelOf(usage({database: 1024 * MiB}, {volume_total_bytes: 10 * GiB, volume_used_bytes: 6 * GiB, volume_free_bytes: 3 * GiB}));

        expect(model.freeBytes).toBe(3 * GiB);
        expect(Math.abs(model.freePercent - 30)).toBeLessThanOrEqual(0.01);
    });

    it('a data folder bigger than the used space of the disk (measured at different moments): no disk segment, never a negative one', async () => {
        const model = await modelOf(usage({database: 3 * GiB, backups: 512 * MiB}, disk(10 * GiB, 1 * GiB)));

        expect(model.mode).toBe('volume');
        expect(ids(model)).toEqual(['database', 'backups']);
        expect(model.segments.every((segment) => segment.percent >= 0 && segment.bytes > 0)).toBe(true);
    });

    it('an empty data folder on a used disk: the disk is the only segment', async () => {
        const model = await modelOf(usage({}, disk(10 * GiB, 6 * GiB)));

        expect(shape(model)).toEqual([{id: 'disk', bytes: 6 * GiB, percent: 60}]);
        expect(model.usedBytes).toBe(6 * GiB);
    });
});

// =====================================================================================================================
describe('storageBarModel — data mode', () => {
    it('the bar is the data folder: shares of the folder, nothing free, no disk', async () => {
        const model = await modelOf(usage({database: 25 * MiB, uploads: 25 * MiB, backups: 50 * MiB}));

        expect(model.mode).toBe('data');
        expect(model.totalBytes).toBe(100 * MiB);
        expect(shape(model)).toEqual([
            {id: 'database', bytes: 25 * MiB, percent: 25},
            {id: 'uploads', bytes: 25 * MiB, percent: 25},
            {id: 'backups', bytes: 50 * MiB, percent: 50},
        ]);
        expect(model.usedBytes).toBe(100 * MiB);
        expect(model.freeBytes).toBe(0);
        expect(model.freePercent).toBe(0);
        expect(model.overLimit).toBe(false);
    });

    it('a usage whose volume is None and which has no limit is data mode', async () => {
        const model = await modelOf(usage({database: 1 * MiB}, {limit_mb: null, volume_total_bytes: null, volume_used_bytes: null, volume_free_bytes: null}));

        expect(model.mode).toBe('data');
        expect(ids(model)).not.toContain('disk');
    });
});

// =====================================================================================================================
describe('storageBarModel — rounding and degenerate bars', () => {
    it('percentages that each round up never add up to more than 100: the last segment is reduced', async () => {
        // Shares 1/6, 1/6, 1/6, 1/6, 1/3 of the data folder: 16.67 × 4 + 33.33 = 100.01 once rounded.
        const model = await modelOf(usage({database: 1, uploads: 1, brokerReports: 1, backups: 1, other: 2}));

        expect(model.mode).toBe('data');
        expect(model.totalBytes).toBe(6);
        expect(ids(model)).toEqual(['database', 'uploads', 'brokerReports', 'backups', 'dataOther']);
        expect(model.segments.slice(0, 4).map((segment) => segment.percent)).toEqual([16.67, 16.67, 16.67, 16.67]);
        expect(sumOfPercents(model)).toBeLessThanOrEqual(100);
        expect(model.segments[4].percent).toBeCloseTo(33.32, 2);
        expect(model.segments.map((segment) => segment.bytes)).toEqual([1, 1, 1, 1, 2]);
    });

    it('a zero total never divides by zero: no segment, nothing used, nothing free, every number finite', async () => {
        const model = await modelOf(usage({}));

        expect(model.mode).toBe('data');
        expect(model.totalBytes).toBe(0);
        expect(model.segments).toEqual([]);
        expect(model.usedBytes).toBe(0);
        expect(model.freeBytes).toBe(0);
        expect(Number.isFinite(model.freePercent)).toBe(true);
        expect(model.freePercent).toBeGreaterThanOrEqual(0);
        expect(model.freePercent).toBeLessThanOrEqual(100);
        expect(model.overLimit).toBe(false);
    });

    it('every percent of every mode is a finite number between 0 and 100', async () => {
        const cases: InstanceStorage[] = [usage({database: 3, uploads: 7}, {limit_mb: 1}), usage({database: 3, uploads: 7}, disk(1000, 500)), usage({database: 3, uploads: 7}), usage({}, disk(1000, 0)), usage({database: 5 * GiB}, {limit_mb: 1})];
        for (const entry of cases) {
            const model = await modelOf(entry);
            for (const percent of [...model.segments.map((segment) => segment.percent), model.freePercent]) {
                expect(Number.isFinite(percent), `${model.mode}: ${percent}`).toBe(true);
                expect(percent).toBeGreaterThanOrEqual(0);
                expect(percent).toBeLessThanOrEqual(100);
            }
            expect(sumOfPercents(model)).toBeLessThanOrEqual(100);
        }
    });

    it('does not change the usage it is given', async () => {
        const entry = usage({database: 100 * MiB, uploads: 50 * MiB}, {limit_mb: 100, ...disk(10 * GiB, 9 * GiB)});
        const before = JSON.stringify(entry);

        await modelOf(entry);

        expect(JSON.stringify(entry)).toBe(before);
    });
});

describe('storageBarModel — a restore under way (C9-7)', () => {
    it('the restore part is drawn after the backups, and only when there is one', async () => {
        const withRestore = await modelOf(usage({database: 10 * MiB, backups: 10 * MiB}, {restore_bytes: 5 * MiB, data_bytes: 25 * MiB, limit_mb: 100} as Partial<InstanceStorage>));
        expect(ids(withRestore)).toEqual(['database', 'backups', 'restore']);
        expect(withRestore.segments.find((segment) => segment.id === 'restore')?.bytes).toBe(5 * MiB);

        const without = await modelOf(usage({database: 10 * MiB}, {limit_mb: 100}));
        expect(ids(without)).not.toContain('restore');
    });
});
