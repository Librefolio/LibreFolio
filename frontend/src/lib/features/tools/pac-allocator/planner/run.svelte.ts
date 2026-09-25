/**
 * One calculation at a time (C4, D7, D15).
 *
 * The run keeps the request it sent, so the result is always shown against
 * the draft revision it describes. Stopping only stops the wait: the server
 * may finish, and that answer is discarded.
 */
import {runTool} from '../../client';
import {ToolClientError, assertToolAccount, type CompatibleToolDescriptor, type ToolBatchMetrics, type ToolItemMetrics} from '../../contracts';
import {notify} from '$lib/stores/app/notify.svelte';
import {PLANNER_CONTRACT_VERSION, PLANNER_TOOL_CODE} from './defaults';
import type {BuiltRequest} from './request';
import type {PacPlannerResult} from './types';

type PlannerDescriptor = CompatibleToolDescriptor<typeof PLANNER_TOOL_CODE, typeof PLANNER_CONTRACT_VERSION>;

export type RunOutcome =
    | {kind: 'result'; built: BuiltRequest; result: PacPlannerResult; metrics: ToolItemMetrics; batch: ToolBatchMetrics; executionId: string | null}
    | {kind: 'tool_error'; built: BuiltRequest; error: {code: string; retryable: boolean; issue_count: number}; metrics: ToolItemMetrics; batch: ToolBatchMetrics}
    | {kind: 'client_error'; built: BuiltRequest; error: ToolClientError};

export class PlannerRun {
    /** The request in flight; `null` when idle. Raw: replaced whole, never edited in place. */
    busy = $state.raw<BuiltRequest | null>(null);
    /** The last completed answer. A stopped wait leaves the previous one in place. Raw: immutable. */
    outcome = $state.raw<RunOutcome | null>(null);
    /** Set when the user stopped waiting; cleared by the next run. */
    stopped = $state(false);

    #descriptor: () => PlannerDescriptor;
    #controller: AbortController | null = null;
    #sequence = 0;

    /** A getter: the renderer props are read when a run starts, never captured. */
    constructor(descriptor: () => PlannerDescriptor) {
        this.#descriptor = descriptor;
    }

    get running(): boolean {
        return this.busy !== null;
    }

    /** A reply for an older run or another account session is dropped (D16). */
    #current(sequence: number, accountGeneration: number): boolean {
        if (sequence !== this.#sequence) return false;
        try {
            assertToolAccount(accountGeneration);
            return true;
        } catch {
            return false;
        }
    }

    async start(built: BuiltRequest, accountGeneration: number): Promise<void> {
        this.#controller?.abort();
        const sequence = ++this.#sequence;
        const controller = new AbortController();
        this.#controller = controller;
        this.busy = built;
        this.stopped = false;
        try {
            const item = await runTool(PLANNER_TOOL_CODE, PLANNER_CONTRACT_VERSION, {
                descriptor: this.#descriptor(),
                correlationId: `pac-rev-${built.revision}-${sequence}`,
                parameters: built.request,
                signal: controller.signal,
            });
            if (!this.#current(sequence, accountGeneration)) return;
            if (item.status === 'success') {
                const result = item.result as PacPlannerResult;
                this.outcome = {kind: 'result', built, result, metrics: item.metrics, batch: item.batch.metrics, executionId: item.execution_id ?? null};
                // Signal for specs and diagnostics: states and counts only, never an amount.
                notify({name: 'tool.pac-plan.completed', detail: {resultState: result.result_state, revision: built.revision, issues: result.issues.length}});
            } else {
                this.outcome = {kind: 'tool_error', built, error: item.error, metrics: item.metrics, batch: item.batch.metrics};
                notify({name: 'tool.pac-plan.failed', detail: {code: item.error.code, retryable: item.error.retryable, revision: built.revision}});
            }
        } catch (caught) {
            if (!this.#current(sequence, accountGeneration)) return;
            const error = caught instanceof ToolClientError ? caught : new ToolClientError('internal', 'unexpected_ui_error');
            if (error.kind === 'aborted') {
                this.stopped = true;
                return;
            }
            // A session change tears the renderer down; nothing to show.
            if (error.kind === 'session' || error.kind === 'authentication') return;
            this.outcome = {kind: 'client_error', built, error};
            notify({name: 'tool.pac-plan.failed', detail: {kind: error.kind, code: error.code, revision: built.revision}});
        } finally {
            if (sequence === this.#sequence) {
                this.busy = null;
                this.#controller = null;
            }
        }
    }

    stop(): void {
        this.#controller?.abort();
    }

    discard(): void {
        this.outcome = null;
    }

    dispose(): void {
        this.#sequence += 1;
        this.#controller?.abort();
        this.#controller = null;
        this.busy = null;
    }
}
