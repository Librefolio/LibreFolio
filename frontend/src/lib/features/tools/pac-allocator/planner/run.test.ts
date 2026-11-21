/**
 * The run keeps the phase the calculation reports (V3 of project 67): the client hands each progress message of the run to
 * `onProgress`; the run keeps the last one, forgets it when the result comes, and ignores a message of a run it superseded.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';

const {runTool, notify} = vi.hoisted(() => ({runTool: vi.fn(), notify: vi.fn()}));

vi.mock('../../client', () => ({runTool}));
vi.mock('$lib/stores/app/notify.svelte', () => ({notify}));
vi.mock('../../contracts', async (importOriginal) => ({...(await importOriginal<object>()), assertToolAccount: () => undefined}));

import type {BuiltRequest} from './request';
import {PlannerRun} from './run.svelte';

const BUILT = {request: {}, resolved: {}, ids: {}, revision: 3, fingerprint: 'f', counts: {assets: 0, operativeBrokers: 0, buyRoutes: 0, fxPairs: 0}} as unknown as BuiltRequest;
const SUCCESS = {status: 'success', result: {result_state: 'ready_no_op', issues: []}, metrics: {}, batch: {metrics: {}}, execution_id: 'x'};

function progress(phase: string): {kind: 'progress'; correlation_id: string; phase: string; step: null; total: null; elapsed_ms: number} {
    return {kind: 'progress', correlation_id: 'c', phase, step: null, total: null, elapsed_ms: 1};
}

afterEach(() => {
    runTool.mockReset();
    notify.mockReset();
});

describe('the run keeps the phase', () => {
    it('the run keeps the last phase received, and forgets it at the result', async () => {
        const seen: (string | null)[] = [];
        let finish: (value: unknown) => void = () => {};
        runTool.mockImplementationOnce((_code, _version, options: {onProgress?: (event: unknown) => void}) => {
            options.onProgress?.(progress('validate'));
            seen.push(run.progress);
            options.onProgress?.(progress('model'));
            options.onProgress?.(progress('search'));
            seen.push(run.progress);
            return new Promise((resolve) => (finish = resolve));
        });
        const run = new PlannerRun(() => ({}) as never);
        expect(run.progress).toBeNull();
        const started = run.start(BUILT, 0);
        await Promise.resolve();
        expect(seen).toEqual(['validate', 'search']);
        expect(run.progress).toBe('search');
        finish(SUCCESS);
        await started;
        expect(run.progress).toBeNull();
    });

    it('a message of a run another one superseded is ignored', async () => {
        let late: (event: unknown) => void = () => {};
        runTool.mockImplementationOnce((_code, _version, options: {onProgress?: (event: unknown) => void}) => {
            late = options.onProgress ?? late;
            return new Promise(() => {});
        });
        runTool.mockImplementationOnce(() => new Promise(() => {}));
        const run = new PlannerRun(() => ({}) as never);
        void run.start(BUILT, 0);
        void run.start(BUILT, 0);
        await Promise.resolve();
        late(progress('verify'));
        expect(run.progress).toBeNull();
        run.dispose();
    });
});
