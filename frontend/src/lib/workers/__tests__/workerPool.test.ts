/**
 * WorkerPool tests.
 *
 * Vitest config in this repo uses default Node environment (`frontend/vitest.config.ts`)
 * instead of a browser-like jsdom/happy-dom environment, so real `Worker`
 * instances are not reliably available here. Tests inject a mock Worker-like
 * object through pool's factory fn and verify public API contract that way.
 */
import {afterEach, describe, expect, it} from 'vitest';

import {WorkerPool, type WorkerRequestMessage, type WorkerResponseMessage} from '../workerPool';

interface TestRequest {
    value: number;
    delayMs?: number;
    failMode?: 'message' | 'throw';
}

interface TestResponse {
    doubled: number;
    workerId: number;
}

class MockWorker {
    public onmessage: ((event: MessageEvent<WorkerResponseMessage<TestResponse>>) => void) | null = null;
    public onerror: ((event: ErrorEvent) => void) | null = null;
    public terminated = false;

    public constructor(private readonly workerId: number) {}

    public postMessage(message: WorkerRequestMessage<TestRequest>): void {
        const delayMs = message.payload.delayMs ?? 0;

        setTimeout(() => {
            if (this.terminated) {
                return;
            }

            if (message.payload.failMode === 'message') {
                this.onmessage?.({
                    data: {
                        id: message.id,
                        error: `mock worker ${this.workerId} rejected payload`,
                    },
                } as MessageEvent<WorkerResponseMessage<TestResponse>>);
                return;
            }

            if (message.payload.failMode === 'throw') {
                this.onerror?.({
                    message: `mock worker ${this.workerId} crashed`,
                    preventDefault: () => undefined,
                } as ErrorEvent);
                return;
            }

            this.onmessage?.({
                data: {
                    id: message.id,
                    result: {
                        doubled: message.payload.value * 2,
                        workerId: this.workerId,
                    },
                },
            } as MessageEvent<WorkerResponseMessage<TestResponse>>);
        }, delayMs);
    }

    public terminate(): void {
        this.terminated = true;
    }
}

const poolsToDestroy: WorkerPool[] = [];

afterEach(() => {
    for (const pool of poolsToDestroy.splice(0)) {
        pool.destroy();
    }
});

function createPool(poolSize: number): {pool: WorkerPool; workers: MockWorker[]} {
    const workers: MockWorker[] = [];
    const pool = new WorkerPool(() => {
        const worker = new MockWorker(workers.length);
        workers.push(worker);
        return worker as unknown as Worker;
    }, poolSize);

    poolsToDestroy.push(pool);
    return {pool, workers};
}

describe('WorkerPool', () => {
    it('resolves single task with worker response', async () => {
        const {pool} = createPool(1);

        await expect(pool.run<TestRequest, TestResponse>({value: 21})).resolves.toEqual({
            doubled: 42,
            workerId: 0,
        });
    });

    it('resolves many concurrent tasks with correct correlation and queueing', async () => {
        const {pool} = createPool(2);

        const results = await Promise.all([pool.run<TestRequest, TestResponse>({value: 1, delayMs: 20}), pool.run<TestRequest, TestResponse>({value: 2, delayMs: 5}), pool.run<TestRequest, TestResponse>({value: 3, delayMs: 0}), pool.run<TestRequest, TestResponse>({value: 4, delayMs: 10})]);

        expect(results.map((result) => result.doubled)).toEqual([2, 4, 6, 8]);
        expect(results.every((result) => result.workerId === 0 || result.workerId === 1)).toBe(true);
        expect(new Set(results.map((result) => result.workerId))).toEqual(new Set([0, 1]));
    });

    it('rejects explicit worker error message without breaking later tasks', async () => {
        const {pool} = createPool(1);

        await expect(pool.run<TestRequest, TestResponse>({value: 7, failMode: 'message'})).rejects.toThrow('Worker task failed: mock worker 0 rejected payload');
        await expect(pool.run<TestRequest, TestResponse>({value: 9})).resolves.toEqual({
            doubled: 18,
            workerId: 0,
        });
    });

    it('rejects worker runtime error and keeps pool usable', async () => {
        const {pool} = createPool(1);

        await expect(pool.run<TestRequest, TestResponse>({value: 5, failMode: 'throw'})).rejects.toThrow('mock worker 0 crashed');
        await expect(pool.run<TestRequest, TestResponse>({value: 6})).resolves.toEqual({
            doubled: 12,
            workerId: 0,
        });
    });

    it('destroy terminates all workers and rejects in-flight tasks', async () => {
        const {pool, workers} = createPool(3);
        const pendingTask = pool.run<TestRequest, TestResponse>({value: 11, delayMs: 30});

        pool.destroy();

        expect(workers).toHaveLength(3);
        expect(workers.every((worker) => worker.terminated)).toBe(true);
        await expect(pendingTask).rejects.toThrow('WorkerPool destroyed before task completion.');
    });
});
