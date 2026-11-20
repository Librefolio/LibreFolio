/**
 * countedQueue — loads that run one at a time, counted from the moment they are asked (project 76, FB-7e).
 *
 * The FX list runs its comparison loads in a chain, one at a time, and says busy (`data-busy`) while one is counted.
 * Before FB-7e a load was counted only when it started: one queued behind a load that is not counted (the silent reload
 * after a price catch-up) waited for it with the page saying settled. A settings save, or its preview, could start such a
 * load. The queue counts a load from its call, so the page says busy for the whole wait.
 */
import {describe, expect, it} from 'vitest';
import {countedQueue} from './countedQueue';

/** A task this test ends by hand, so that «running» and «queued» are states it controls. */
function manual(): {task: () => Promise<void>; started: () => boolean; finish: () => void} {
    let started = false;
    let finish!: () => void;
    const done = new Promise<void>((resolve) => (finish = resolve));
    return {
        task: () => {
            started = true;
            return done;
        },
        started: () => started,
        finish: () => finish(),
    };
}

const settle = () => new Promise<void>((resolve) => setTimeout(resolve, 0));

describe('countedQueue', () => {
    it('counts a load from its call, before it starts', () => {
        let count = 0;
        const queue = countedQueue((delta) => (count += delta));
        const load = manual();
        void queue.run(load.task, true);
        expect(count, 'counted at once').toBe(1);
        expect(load.started(), 'the task itself starts a step later').toBe(false);
    });

    it('counts a load queued behind one that is not counted (the silent reload) for the whole wait, then lets go', async () => {
        let count = 0;
        const queue = countedQueue((delta) => (count += delta));
        const silent = manual();
        const saved = manual();
        void queue.run(silent.task, false);
        const savedDone = queue.run(saved.task, true);
        await settle();
        expect([silent.started(), saved.started()], 'the silent load runs, the saved one waits').toEqual([true, false]);
        expect(count, 'the page says busy while the saved load waits').toBe(1);

        silent.finish();
        await settle();
        expect(saved.started()).toBe(true);
        expect(count).toBe(1);
        saved.finish();
        await savedDone;
        expect(count).toBe(0);
    });

    it('runs the loads one at a time, in the order asked', async () => {
        const order: string[] = [];
        const queue = countedQueue(() => undefined);
        const first = manual();
        void queue.run(async () => {
            order.push('first');
            await first.task();
        }, true);
        const second = queue.run(async () => {
            order.push('second');
        }, true);
        await settle();
        expect(order).toEqual(['first']);
        first.finish();
        await second;
        expect(order).toEqual(['first', 'second']);
    });

    it('lets go of the count when a load fails, and hands the failure to its caller', async () => {
        let count = 0;
        const queue = countedQueue((delta) => (count += delta));
        await expect(queue.run(() => Promise.reject(new Error('refused')), true)).rejects.toThrow('refused');
        expect(count).toBe(0);
    });

    it('never counts a load asked as not counted', async () => {
        const deltas: number[] = [];
        const queue = countedQueue((delta) => deltas.push(delta));
        await queue.run(async () => undefined, false);
        expect(deltas).toEqual([]);
    });
});
