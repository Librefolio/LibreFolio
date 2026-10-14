/**
 * What a step shows after an explicit copy: the notice, then the conflict
 * dialog when a re-copy found facts the user had changed (B4).
 */
import {resolveConflicts, type CopyConflict, type CopyOutcome} from './copies';
import type {CopyRecord, PlannerDraft} from './draft.svelte';
import type {PlannerSource} from './source';

export class CopyFlow {
    notice = $state<{outcome: CopyOutcome; source: PlannerSource} | null>(null);
    pending = $state<{copy: CopyRecord; conflicts: CopyConflict[]} | null>(null);

    accept(outcome: CopyOutcome, source: PlannerSource): void {
        this.notice = {outcome, source};
        this.pending = outcome.conflicts.length > 0 ? {copy: outcome.copy, conflicts: outcome.conflicts} : null;
    }

    resolve(draft: PlannerDraft, choice: 'keep' | 'update'): void {
        if (this.pending) resolveConflicts(draft, this.pending.copy, this.pending.conflicts, choice);
        this.pending = null;
    }

    dismiss(): void {
        this.notice = null;
    }
}
