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

  A notice whose `context.report_issue` is `true` carries, under its message, the fix step's link «open an issue on
  GitHub» (`importWizard.fixStep.reportIssueLink`), on every instance. Two uses: a warning for rows the plugin left out
  because it does not know them (W-B85, Danske Bank's `excluded_status`), and a note from a plugin in beta that suspects
  its own reading (Fineco's `fineco_incomplete_rows`, W-B83).

  Legacy plugins that append plain strings are coerced backend-side into
  `{severity: 'warning', code: 'generic', message: <string>}`, so this component
  never has to deal with bare strings.
-->
<script lang="ts">
    import {AlertTriangle, Info} from 'lucide-svelte';
    import {t} from 'svelte-i18n';
    import BrimEvidenceTable from './BrimEvidenceTable.svelte';
    import {resolveBrimEvidenceComment, resolveBrimNoticeMessage} from '$lib/features/transactions/resolveBrimNotice';
    import {GITHUB_NEW_ISSUE_URL} from '$lib/components/assets/assetSearchReport';
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

    /** Whether the plugin asks the user to report its reading (`context.report_issue`, the boolean `true` only). */
    function reportsIssue(notice: BrimNotice): boolean {
        return (notice.context as Record<string, unknown> | null | undefined)?.report_issue === true;
    }
</script>

<ul class={dense ? 'space-y-1.5' : 'space-y-2'} data-testid="brim-notice-list">
    {#each notices as notice}
        {@const severity = severityOf(notice)}
        <li class="flex items-start gap-2" data-testid="brim-notice" data-severity={severity}>
            {#if severity === 'info'}
                <Info size={dense ? 12 : 14} class="mt-0.5 shrink-0 text-lf-info" />
            {:else}
                <AlertTriangle size={dense ? 12 : 14} class="mt-0.5 shrink-0 text-lf-warning" />
            {/if}
            <div class="min-w-0 flex-1 space-y-1.5">
                <p class="{dense ? 'text-xs' : 'text-sm'} leading-relaxed whitespace-pre-line {severity === 'info' ? 'text-lf-info' : 'text-lf-warning'}" data-testid="brim-notice-message">
                    {resolveBrimNoticeMessage(notice, $t)}
                </p>
                {#if reportsIssue(notice)}
                    <a
                        href={GITHUB_NEW_ISSUE_URL}
                        target="_blank"
                        rel="noopener noreferrer"
                        class="inline-block {dense ? 'text-xs' : 'text-sm'} font-medium underline underline-offset-2 hover:opacity-80 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus {severity === 'info' ? 'text-lf-info' : 'text-lf-warning'}"
                        data-testid="brim-notice-report-issue">{$t('importWizard.fixStep.reportIssueLink')}</a
                    >
                {/if}
                {#each notice.evidence ?? [] as evidence}
                    <BrimEvidenceTable evidence={{...evidence, title: evidence.title || $t('importWizard.evidenceRowsTitle'), comment: resolveBrimEvidenceComment(notice, evidence.comment, $t)}} tone={severity} collapsible={collapsibleEvidence} {onGotoRow} />
                {/each}
            </div>
        </li>
    {/each}
</ul>
