<!--
  BrimNoticeList.svelte — P1 Crédit Agricole pre-alarm net

  Renders a list of `BrimNotice` entries produced by a BRIM plugin.

  Two severities, two colours:
    - `info`    → sky/blue: the plugin explains a deliberate choice it made
                  (e.g. "these 36 rows are transfers, booked as adjustments").
    - `warning` → amber: something needs the user's attention.

  Both severities still trigger the Step 3 confirmation modal — an `info` notice
  is not noise to be skipped, it is a decision the user should be aware of before
  the data lands in the portfolio.

  Legacy plugins that append plain strings are coerced backend-side into
  `{severity: 'warning', code: 'generic', message: <string>}`, so this component
  never has to deal with bare strings.
-->
<script lang="ts">
    import {AlertTriangle, Info} from 'lucide-svelte';
    import {t} from 'svelte-i18n';
    import BrimEvidenceTable from './BrimEvidenceTable.svelte';
    import {resolveBrimNoticeMessage} from '$lib/utils/transactions/resolveBrimNotice';
    import type {BrimNotice} from '$lib/types';

    interface Props {
        notices: BrimNotice[];
        /** Compact spacing for dense contexts (confirmation modal accordions). */
        dense?: boolean;
        /** Fold the evidence tables behind a toggle — see `BrimEvidenceTable`. */
        collapsibleEvidence?: boolean;
        /** Open the source file at a given 1-based line — see `BrimEvidenceTable`. */
        onGotoRow?: (rowNumbers: number[]) => void;
    }

    let {notices, dense = false, collapsibleEvidence = false, onGotoRow}: Props = $props();

    function severityOf(notice: BrimNotice): 'info' | 'warning' {
        return notice.severity === 'info' ? 'info' : 'warning';
    }
</script>

<ul class={dense ? 'space-y-1.5' : 'space-y-2'} data-testid="brim-notice-list">
    {#each notices as notice}
        {@const severity = severityOf(notice)}
        <li class="flex items-start gap-2" data-testid="brim-notice" data-severity={severity}>
            {#if severity === 'info'}
                <Info size={dense ? 12 : 14} class="mt-0.5 shrink-0 text-sky-600 dark:text-sky-400" />
            {:else}
                <AlertTriangle size={dense ? 12 : 14} class="mt-0.5 shrink-0 text-amber-600 dark:text-amber-400" />
            {/if}
            <div class="min-w-0 flex-1 space-y-1.5">
                <p class="{dense ? 'text-xs' : 'text-sm'} leading-relaxed whitespace-pre-line {severity === 'info' ? 'text-sky-800 dark:text-sky-300' : 'text-amber-700 dark:text-amber-400'}" data-testid="brim-notice-message">
                    {resolveBrimNoticeMessage(notice, $t)}
                </p>
                {#each notice.evidence ?? [] as evidence}
                    <BrimEvidenceTable {evidence} tone={severity} collapsible={collapsibleEvidence} {onGotoRow} />
                {/each}
            </div>
        </li>
    {/each}
</ul>
