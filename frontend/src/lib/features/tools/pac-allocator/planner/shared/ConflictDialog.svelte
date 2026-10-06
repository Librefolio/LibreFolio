<script lang="ts">
    import {t, locale} from '$lib/i18n';
    import type {CopyConflict} from '../copies';
    import type {CopyRecord, CopyRef, PlannerDraft} from '../draft.svelte';
    import {formatPlannerMoneyPlain, formatPlannerTimestamp} from '../format';
    import {BUTTON_PRIMARY, BUTTON_SECONDARY, HINT} from '../ui';
    import PlannerDialog from './PlannerDialog.svelte';

    interface Props {
        open: boolean;
        draft: PlannerDraft;
        copy: CopyRecord | null;
        conflicts: readonly CopyConflict[];
        onresolve: (choice: 'keep' | 'update') => void;
    }

    let {open, draft, copy, conflicts, onresolve}: Props = $props();

    const title = $derived(
        conflicts.length === 1
            ? $t('tools.pacAllocator.planner.conflict.titleOne', {default: '{name} changed since the last copy', values: {name: conflicts[0].label}})
            : $t('tools.pacAllocator.planner.conflict.titleMany', {default: '{count} copied facts changed since the last copy', values: {count: conflicts.length}}),
    );

    function copiedAt(stamp: CopyRef | null): string {
        const record = draft.copyRecord(stamp);
        return record ? formatPlannerTimestamp(record.capturedAt, $locale) : '—';
    }

    const incomingAt = $derived(copy ? formatPlannerTimestamp(copy.capturedAt, $locale) : '—');
</script>

<PlannerDialog {open} {title} testid="pac-planner-conflict" onclose={() => onresolve('keep')} zIndex={60}>
    <p>{$t('tools.pacAllocator.planner.conflict.intro', {default: 'You asked to copy again. These facts are different now:'})}</p>
    <ul class="space-y-3">
        {#each conflicts as conflict (conflict.id)}
            <li class="space-y-1 rounded-lg border border-gray-200 p-3 dark:border-gray-700" data-testid="pac-planner-conflict-row" data-kind={conflict.kind}>
                <p class="font-medium">{conflict.label} · {conflict.currency}</p>
                <dl class="grid grid-cols-[minmax(0,1fr)_auto] gap-x-4 gap-y-1">
                    <dt>{$t('tools.pacAllocator.planner.conflict.cashPrevious', {default: 'Balance copied in the draft · {date}', values: {date: copiedAt(conflict.previousStamp)}})}</dt>
                    <dd class="text-right tabular-nums" data-testid="pac-planner-conflict-previous">{formatPlannerMoneyPlain(conflict.previous, conflict.currency)}</dd>
                    <dt>{$t('tools.pacAllocator.planner.conflict.cashIncoming', {default: 'Balance from the system · {date}', values: {date: incomingAt}})}</dt>
                    <dd class="text-right tabular-nums" data-testid="pac-planner-conflict-incoming">{formatPlannerMoneyPlain(conflict.incoming, conflict.currency)}</dd>
                    <dt>{$t('tools.pacAllocator.planner.conflict.cashSelected', {default: 'Amount to use (yours) · does not change'})}</dt>
                    <dd class="text-right tabular-nums">{formatPlannerMoneyPlain(conflict.selected, conflict.currency)}</dd>
                </dl>
            </li>
        {/each}
    </ul>
    <p class={HINT}>{$t('tools.pacAllocator.planner.conflict.rule', {default: 'Updating changes only the copied fact and its date. Your fields stay as they are.'})}</p>

    {#snippet footer()}
        <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-conflict-keep" onclick={() => onresolve('keep')}>
            {$t('tools.pacAllocator.planner.conflict.keep', {default: 'Keep previous copy'})}
        </button>
        <button type="button" class={BUTTON_PRIMARY} data-testid="pac-planner-conflict-update" onclick={() => onresolve('update')}>
            {$t('tools.pacAllocator.planner.conflict.update', {default: 'Update copied fact'})}
        </button>
    {/snippet}
</PlannerDialog>
