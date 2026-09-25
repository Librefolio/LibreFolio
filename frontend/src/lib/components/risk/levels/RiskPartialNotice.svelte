<script lang="ts">
    import {AlertTriangle} from 'lucide-svelte';

    import {_ as t} from '$lib/i18n';

    import type {ResultHealth, ResultReason} from './levelHelpers';
    import {analyticNameKey} from './partialNotice';

    /**
     * What is partial, and why, said once above the levels (developer's decision of 24/09/2026).
     *
     * The levels used to repeat it one by one, so the same carried-over price or excluded asset
     * read as four separate problems. Two titles, because a note on a complete result is still
     * worth reading but must not be introduced as a partial one.
     */
    interface Props {
        partial: ResultHealth[];
        reasons: ResultReason[];
    }

    let {partial, reasons}: Props = $props();

    function measurementName(entry: ResultHealth): string {
        return entry.label ? $t(entry.label) : $t(analyticNameKey(entry.code), {default: entry.code});
    }
</script>

{#if partial.length > 0 || reasons.length > 0}
    <div class="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-300" data-testid="risk-partial-notice" data-partial-count={partial.length}>
        <p class="flex items-center gap-1.5 font-medium" data-testid="risk-partial-title">
            <AlertTriangle size={14} class="shrink-0" />
            {partial.length > 0 ? $t('risk.levels.notice.partialTitle') : $t('risk.levels.notice.notesTitle')}
        </p>
        {#if partial.length > 0}
            <!-- Per instance, never per analytic code: the two VaR horizons share a code and are told
                 apart by their label, so `data-count` publishes how many measurements are partial. -->
            <p class="mt-1" data-testid="risk-partial-measurements" data-count={partial.length}>
                {partial.map((entry) => measurementName(entry)).join(' · ')}
            </p>
        {/if}
        {#if reasons.length > 0}
            <ul class="mt-1 list-disc space-y-0.5 pl-5" data-testid="risk-partial-reasons" data-count={reasons.length}>
                {#each reasons as reason (reason.key)}
                    <li data-testid="risk-partial-reason" data-occurrences={reason.occurrences}>{reason.message}</li>
                {/each}
            </ul>
        {/if}
    </div>
{/if}
