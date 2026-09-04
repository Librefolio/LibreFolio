import {describe, it, expect, vi} from 'vitest';
import {mapWithConcurrency, requestConcurrency, HTTP1_PER_HOST_LIMIT, DEFAULT_CONCURRENCY} from '../core/requestConcurrency';

/**
 * The import wizard uploads and parses several files per run. Both loops used to be
 * strictly sequential; they now go through this runner, so its two promises — **order is
 * preserved** and **the limit is respected** — are load-bearing:
 *
 * - the wizard indexes `parseResults` by position, so a runner returning results in
 *   completion order would silently attach a file's transactions to another file;
 * - the abort button must actually stop the run, and stopping means "start nothing new",
 *   because a request already sent cannot be unsent.
 */

/** A task that records how many run at the same time, so the cap can be asserted. */
function tracker(delayFor: (n: number) => number = () => 0) {
    let inFlight = 0;
    let peak = 0;
    const order: number[] = [];
    const task = async (n: number) => {
        inFlight += 1;
        peak = Math.max(peak, inFlight);
        await new Promise((r) => setTimeout(r, delayFor(n)));
        order.push(n);
        inFlight -= 1;
        return n * 2;
    };
    return {
        task,
        get peak() {
            return peak;
        },
        get order() {
            return order;
        },
    };
}

describe('requestConcurrency', () => {
    it('leaves one connection free for the rest of the app', () => {
        vi.spyOn(navigator, 'hardwareConcurrency', 'get').mockReturnValue(16);
        expect(requestConcurrency()).toBe(HTTP1_PER_HOST_LIMIT - 1);
        vi.restoreAllMocks();
    });

    it('never asks for more parallelism than there are cores', () => {
        vi.spyOn(navigator, 'hardwareConcurrency', 'get').mockReturnValue(2);
        expect(requestConcurrency()).toBe(2);
        vi.restoreAllMocks();
    });

    it('stays at 2 on a single-core machine — one at a time is not worth a runner', () => {
        vi.spyOn(navigator, 'hardwareConcurrency', 'get').mockReturnValue(1);
        expect(requestConcurrency()).toBe(2);
        vi.restoreAllMocks();
    });

    it('falls back to a fixed default when the browser will not say', () => {
        vi.spyOn(navigator, 'hardwareConcurrency', 'get').mockReturnValue(undefined as unknown as number);
        expect(requestConcurrency()).toBe(DEFAULT_CONCURRENCY);
        vi.restoreAllMocks();
    });
});

describe('mapWithConcurrency', () => {
    it('returns results in input order even when tasks finish out of order', async () => {
        // Descending delays: the last item finishes first.
        const {task} = tracker((n) => (5 - n) * 5);
        const out = await mapWithConcurrency([0, 1, 2, 3, 4], task, {limit: 5});
        expect(out).toEqual([0, 2, 4, 6, 8]);
    });

    it('never exceeds the limit', async () => {
        const t = tracker(() => 5);
        await mapWithConcurrency([1, 2, 3, 4, 5, 6, 7, 8], t.task, {limit: 3});
        expect(t.peak).toBe(3);
    });

    it('does not spawn more workers than there are items', async () => {
        const t = tracker(() => 5);
        await mapWithConcurrency([1, 2], t.task, {limit: 10});
        expect(t.peak).toBe(2);
    });

    it('is a no-op on an empty list', async () => {
        const task = vi.fn();
        expect(await mapWithConcurrency([], task)).toEqual([]);
        expect(task).not.toHaveBeenCalled();
    });

    it('stops starting new tasks once shouldStop turns true', async () => {
        const started: number[] = [];
        let stop = false;
        await mapWithConcurrency(
            [1, 2, 3, 4, 5, 6],
            async (n) => {
                started.push(n);
                if (started.length >= 2) stop = true;
                return n;
            },
            {limit: 1, shouldStop: () => stop},
        );
        expect(started).toEqual([1, 2]);
    });

    it('leaves untouched slots undefined when aborted', async () => {
        let stop = false;
        const out = await mapWithConcurrency(
            [1, 2, 3, 4],
            async (n) => {
                if (n === 2) stop = true;
                return n * 10;
            },
            {limit: 1, shouldStop: () => stop},
        );
        expect(out).toEqual([10, 20, undefined, undefined]);
    });

    it('runs every item when the limit exceeds the list length', async () => {
        const out = await mapWithConcurrency([1, 2, 3], async (n) => n + 1, {limit: 99});
        expect(out).toEqual([2, 3, 4]);
    });

    it('surfaces a rejection instead of hiding it', async () => {
        await expect(
            mapWithConcurrency([1, 2, 3], async (n) => {
                if (n === 2) throw new Error('boom');
                return n;
            }),
        ).rejects.toThrow('boom');
    });
});
