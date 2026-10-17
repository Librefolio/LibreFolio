/**
 * The pending retry of a scheduler job, for the status row of the scheduler (workstream Z, lot Z7c-2).
 *
 * After a job that raised, the scheduler waits before it runs it again (`next_attempt_at`); items a provider's pause
 * deferred are retried at `retry_at`. Only a moment still ahead is shown: the wait after a failure first.
 */

export interface SchedulerJobRetryFields {
    retry_at?: string | null;
    next_attempt_at?: string | null;
}

export interface PendingSchedulerRetry {
    kind: 'failure' | 'deferred';
    at: Date;
}

function ahead(value: string | null | undefined, now: number): Date | null {
    if (!value) return null;
    const at = new Date(value);
    return at.getTime() > now ? at : null;
}

/** The job's next attempt after a failure, else its deferred items' retry, when still ahead of `now`; else null. */
export function pendingSchedulerRetry(job: SchedulerJobRetryFields | null | undefined, now: number): PendingSchedulerRetry | null {
    if (!job) return null;
    const failure = ahead(job.next_attempt_at, now);
    if (failure) return {kind: 'failure', at: failure};
    const deferred = ahead(job.retry_at, now);
    return deferred ? {kind: 'deferred', at: deferred} : null;
}
