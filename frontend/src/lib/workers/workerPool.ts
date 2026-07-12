const DEFAULT_WORKER_POOL_SIZE = 4;
const MAX_WORKER_POOL_SIZE = 8;

/**
 * Factory used by {@link WorkerPool} to create each long-lived worker instance.
 *
 * Pool stays decoupled from any specific worker script: callers provide the
 * `new Worker(new URL(...), {type: 'module'})` logic that matches their task.
 */
export type WorkerFactory = () => Worker;

/**
 * Message shape sent from {@link WorkerPool} to worker script.
 *
 * `id` lets pool correlate responses back to correct `run()` promise. Worker
 * authors should echo same `id` in their response message.
 */
export interface WorkerRequestMessage<TPayload> {
    id: string;
    payload: TPayload;
}

/**
 * Success message shape worker scripts should post back to pool.
 */
export interface WorkerSuccessResponseMessage<TResult> {
    id: string;
    result: TResult;
}

/**
 * Error message shape worker scripts should post back when task-specific work
 * fails but worker itself can stay alive for future tasks.
 */
export interface WorkerErrorResponseMessage {
    id: string;
    error: string;
}

/**
 * Union of supported worker → pool response messages.
 */
export type WorkerResponseMessage<TResult> = WorkerSuccessResponseMessage<TResult> | WorkerErrorResponseMessage;

interface QueuedTask<TRequest = unknown> {
    id: string;
    payload: TRequest;
    resolve: (value: unknown) => void;
    reject: (reason?: unknown) => void;
}

interface WorkerSlot {
    worker: Worker;
    activeTask: QueuedTask | null;
}

/**
 * Generic pool for browser Web Workers.
 *
 * Design choices:
 * - Pool size defaults to `navigator.hardwareConcurrency` because browser can
 *   report rough CPU parallelism. That value is capped to avoid oversubscribing
 *   mid-sized tasks on big machines, and a safe fallback is used for SSR/tests
 *   where `navigator` does not exist.
 * - Workers are created once per pool instance and kept alive for pool lifetime.
 *   Reusing hot workers avoids repeated startup/module-init cost on every task.
 * - Constructor receives a worker factory instead of worker URL. That keeps pool
 *   task-agnostic, so future worker scripts can reuse same scheduling/error
 *   handling without coupling infrastructure to one concrete module.
 *
 * Scheduling currently uses round-robin over idle workers. That keeps first
 * implementation predictable and cheap. Future callers with highly uneven task
 * costs could upgrade this to a least-busy strategy.
 */
export class WorkerPool {
    private readonly workers: WorkerSlot[];
    private readonly taskQueue: QueuedTask[] = [];
    private nextWorkerIndex = 0;
    private nextTaskId = 0;
    private destroyed = false;

    public constructor(
        private readonly workerFactory: WorkerFactory,
        poolSize: number = getDefaultWorkerPoolSize(),
    ) {
        const normalizedPoolSize = normalizePoolSize(poolSize);
        this.workers = Array.from({length: normalizedPoolSize}, () => this.createWorkerSlot());
    }

    /**
     * Queue one logical unit of work for pool.
     *
     * Multiple `run()` calls can stay pending at same time. Pool dispatches up to
     * one active task per worker in parallel, then queues overflow until a worker
     * becomes idle.
     */
    public run<TRequest, TResponse>(payload: TRequest): Promise<TResponse> {
        if (this.destroyed) {
            return Promise.reject(new Error('WorkerPool has been destroyed.'));
        }

        return new Promise<TResponse>((resolve, reject) => {
            this.taskQueue.push({
                id: this.createTaskId(),
                payload,
                resolve: (value: unknown) => resolve(value as TResponse),
                reject,
            });

            this.schedule();
        });
    }

    /**
     * Terminate all workers and reject any queued/in-flight tasks.
     *
     * Useful for component teardown, tests, or app shutdown paths.
     */
    public destroy(): void {
        if (this.destroyed) {
            return;
        }

        this.destroyed = true;
        const error = new Error('WorkerPool destroyed before task completion.');

        for (const task of this.taskQueue.splice(0)) {
            task.reject(error);
        }

        for (const slot of this.workers) {
            if (slot.activeTask) {
                slot.activeTask.reject(error);
                slot.activeTask = null;
            }

            slot.worker.onmessage = null;
            slot.worker.onerror = null;
            slot.worker.terminate();
        }
    }

    /**
     * Alias for {@link destroy} to mirror native `Worker#terminate()` naming.
     */
    public terminate(): void {
        this.destroy();
    }

    private createWorkerSlot(): WorkerSlot {
        const worker = this.workerFactory();
        const slot: WorkerSlot = {
            worker,
            activeTask: null,
        };

        worker.onmessage = (event: MessageEvent<WorkerResponseMessage<unknown>>) => {
            this.handleWorkerMessage(slot, event.data);
        };
        worker.onerror = (event: ErrorEvent) => {
            event.preventDefault?.();
            this.handleWorkerError(slot, event);
        };

        return slot;
    }

    private schedule(): void {
        while (!this.destroyed && this.taskQueue.length > 0) {
            const slot = this.getNextIdleWorker();
            if (!slot) {
                return;
            }

            const task = this.taskQueue.shift();
            if (!task) {
                return;
            }

            slot.activeTask = task;

            try {
                const requestMessage: WorkerRequestMessage<unknown> = {
                    id: task.id,
                    payload: task.payload,
                };
                slot.worker.postMessage(requestMessage);
            } catch (error) {
                slot.activeTask = null;
                task.reject(toWorkerPoolError(error, 'Failed to post message to worker.'));
            }
        }
    }

    private getNextIdleWorker(): WorkerSlot | null {
        for (let offset = 0; offset < this.workers.length; offset += 1) {
            const index = (this.nextWorkerIndex + offset) % this.workers.length;
            const slot = this.workers[index];
            if (!slot.activeTask) {
                this.nextWorkerIndex = (index + 1) % this.workers.length;
                return slot;
            }
        }

        return null;
    }

    private handleWorkerMessage(slot: WorkerSlot, message: WorkerResponseMessage<unknown>): void {
        const activeTask = slot.activeTask;
        if (!activeTask || this.destroyed) {
            return;
        }

        slot.activeTask = null;

        if (!isWorkerResponseMessage(message)) {
            activeTask.reject(new Error('Worker returned invalid response message.'));
            this.schedule();
            return;
        }

        if (message.id !== activeTask.id) {
            activeTask.reject(new Error(`Worker response id mismatch. Expected "${activeTask.id}", got "${message.id}".`));
            this.schedule();
            return;
        }

        if ('error' in message) {
            activeTask.reject(new Error(`Worker task failed: ${message.error}`));
            this.schedule();
            return;
        }

        activeTask.resolve(message.result);
        this.schedule();
    }

    private handleWorkerError(slot: WorkerSlot, event: ErrorEvent): void {
        const activeTask = slot.activeTask;
        if (!activeTask || this.destroyed) {
            return;
        }

        slot.activeTask = null;
        activeTask.reject(new Error(event.message || 'Worker execution failed.'));
        this.schedule();
    }

    private createTaskId(): string {
        const taskId = this.nextTaskId;
        this.nextTaskId += 1;
        return `worker-pool-task-${taskId}`;
    }
}

/**
 * Compute default pool size for browser workloads.
 *
 * In SSR, tests, or other non-browser contexts `navigator` can be missing, so
 * this falls back to a conservative fixed size.
 */
export function getDefaultWorkerPoolSize(): number {
    if (typeof navigator === 'undefined') {
        return DEFAULT_WORKER_POOL_SIZE;
    }

    const {hardwareConcurrency} = navigator;
    if (!Number.isFinite(hardwareConcurrency) || hardwareConcurrency < 1) {
        return DEFAULT_WORKER_POOL_SIZE;
    }

    return Math.min(MAX_WORKER_POOL_SIZE, Math.max(1, Math.floor(hardwareConcurrency)));
}

function normalizePoolSize(poolSize: number): number {
    if (!Number.isInteger(poolSize) || poolSize < 1) {
        throw new RangeError('WorkerPool size must be a positive integer.');
    }

    return poolSize;
}

function isWorkerResponseMessage(value: unknown): value is WorkerResponseMessage<unknown> {
    if (!value || typeof value !== 'object') {
        return false;
    }

    const candidate = value as Partial<WorkerSuccessResponseMessage<unknown> & WorkerErrorResponseMessage>;
    const hasStringId = typeof candidate.id === 'string';
    const hasResult = 'result' in candidate;
    const hasError = typeof candidate.error === 'string';

    return hasStringId && (hasResult || hasError);
}

function toWorkerPoolError(error: unknown, fallbackMessage: string): Error {
    if (error instanceof Error) {
        return error;
    }

    if (typeof error === 'string' && error.length > 0) {
        return new Error(error);
    }

    return new Error(fallbackMessage);
}
