<script lang="ts">
    import {t, locale} from '$lib/i18n';
    import type {CopyKind} from '../draft.svelte';
    import type {PlannerDraft} from '../draft.svelte';
    import type {CopyOutcome} from '../copies';
    import {formatPlannerDate, formatPlannerTimestamp} from '../format';
    import {presentSourceIssues} from '../issues';
    import {listIssue} from '../labels';
    import type {PlannerSource} from '../source';
    import {BUTTON_LINK, NOTICE} from '../ui';
    import IssueList from './IssueList.svelte';

    interface Props {
        outcome: CopyOutcome;
        draft: PlannerDraft;
        source: PlannerSource | null;
        testid: string;
        ondismiss: () => void;
    }

    let {outcome, draft, source, testid, ondismiss}: Props = $props();

    const MISSING_FALLBACKS: Partial<Record<CopyKind, string>> = {
        prices: 'No price published for: {names}. They stay in the draft; the calculation will ask for them.',
        classifications: 'No complete classification for: {names}.',
        fx: 'No rate published for: {names}.',
        liquidity: 'Nothing copied for: {names}.',
        brokers: 'Nothing copied for: {names}.',
    };

    const issues = $derived(presentSourceIssues(outcome.issues, draft, source).map(listIssue));
    const warn = $derived(outcome.missing.length > 0 || outcome.conflicts.length > 0 || issues.some((item) => item.severity !== 'info'));
</script>

<div class={warn ? NOTICE.warning : NOTICE.success} role="status" data-testid={testid} data-kind={outcome.kind} data-applied={outcome.applied} data-unchanged={outcome.unchanged} data-missing={outcome.missing.length} data-conflicts={outcome.conflicts.length}>
    <div class="flex flex-wrap items-start justify-between gap-2">
        <div class="min-w-0 space-y-1">
            <p class="font-medium">
                {$t('tools.pacAllocator.planner.copyNotice.summary', {
                    default: 'Copy done: {applied} added or updated, {unchanged} unchanged.',
                    values: {applied: outcome.applied, unchanged: outcome.unchanged},
                })}
            </p>
            <p class="text-xs">
                {$t('tools.pacAllocator.planner.copyNotice.when', {
                    default: 'Snapshot at {date}, read {time}. Nothing stays linked to the source.',
                    values: {date: formatPlannerDate(outcome.copy.asOf, $locale), time: formatPlannerTimestamp(outcome.copy.capturedAt, $locale)},
                })}
            </p>
            {#if outcome.missing.length > 0}
                <p data-testid="{testid}-missing">
                    {$t(`tools.pacAllocator.planner.copyNotice.missing.${outcome.kind}`, {default: MISSING_FALLBACKS[outcome.kind] ?? '{names}', values: {names: outcome.missing.join(', ')}})}
                </p>
            {/if}
            {#if outcome.conflicts.length > 0}
                <p data-testid="{testid}-conflicts">
                    {$t('tools.pacAllocator.planner.copyNotice.conflicts', {
                        default: '{count, plural, one {# fact changed since the previous copy: you decide in the dialog.} other {# facts changed since the previous copy: you decide in the dialog.}}',
                        values: {count: outcome.conflicts.length},
                    })}
                </p>
            {/if}
        </div>
        <button type="button" class={BUTTON_LINK} data-testid="{testid}-dismiss" onclick={ondismiss}>{$t('common.close', {default: 'Close'})}</button>
    </div>
    {#if issues.length > 0}
        <div class="mt-2">
            <IssueList items={issues} testid="{testid}-issues" />
        </div>
    {/if}
</div>
