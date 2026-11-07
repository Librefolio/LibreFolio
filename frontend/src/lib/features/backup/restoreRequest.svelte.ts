/**
 * «Restore» on a row of the kept backups (C9-9): the request travels to the restore card, wherever the list is shown.
 *
 * The list sits in Settings › Backup, beside the restore card, and in Files › Backups, which has no card: the row asks
 * here, the page then goes to Settings › Backup if needed, and the card takes the request as soon as it can (mounted, its
 * state read, nothing else under way) and forgets it.
 */
export const restoreRequest = $state<{jobId: string | null}>({jobId: null});

/** Ask the restore card to restore the kept backup `jobId`. */
export function requestRestoreFromKept(jobId: string): void {
    restoreRequest.jobId = jobId;
}

/** The pending request, taken by the card: it is forgotten here. */
export function takeRestoreRequest(): string | null {
    const jobId = restoreRequest.jobId;
    restoreRequest.jobId = null;
    return jobId;
}
