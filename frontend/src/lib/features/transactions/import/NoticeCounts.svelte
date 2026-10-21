<!--
  NoticeCounts.svelte — the warnings and the notes of a BRIM parse, as two counts (B-51).

  An amber triangle for the warnings (something needs the user's attention) and a blue «i» for the notes (the plugin
  explains a choice it made): the icons and colours of `BrimNoticeList` and of the step-3 confirmation. A zero is
  muted, its icon included, so a file whose only notices are notes never lights the amber; no opacity, which the
  design system forbids on a notice (rule 12). Each count is named for screen readers.

  Read by the results column of the analysis step (`noticeCountsCell`, size `sm`) and by its stats tile (`lg`).
-->
<script lang="ts">
    import {AlertTriangle, Info} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';

    interface Props {
        warnings: number;
        notes: number;
        /** `sm` in a table cell; `lg` in a stats tile, which gives the font. */
        size?: 'sm' | 'lg';
    }

    let {warnings, notes, size = 'sm'}: Props = $props();

    let iconSize = $derived(size === 'lg' ? 16 : 13);
</script>

<span class="inline-flex items-center gap-2 tabular-nums" data-testid="notice-counts" data-warnings={warnings} data-notes={notes}>
    <span class="inline-flex items-center gap-0.5 {warnings > 0 ? 'text-lf-warning' : 'text-lf-muted'} {size === 'sm' && warnings > 0 ? 'font-medium' : ''}" data-testid="notice-count" data-severity="warning" data-count={warnings} data-zero={warnings === 0 ? 'true' : 'false'}>
        <AlertTriangle size={iconSize} class="shrink-0" aria-hidden="true" />
        <span aria-hidden="true">{warnings}</span>
        <span class="sr-only">{$t('importWizard.warningsCount', {values: {n: warnings}})}</span>
    </span>
    <span class="inline-flex items-center gap-0.5 {notes > 0 ? 'text-lf-info' : 'text-lf-muted'} {size === 'sm' && notes > 0 ? 'font-medium' : ''}" data-testid="notice-count" data-severity="info" data-count={notes} data-zero={notes === 0 ? 'true' : 'false'}>
        <Info size={iconSize} class="shrink-0" aria-hidden="true" />
        <span aria-hidden="true">{notes}</span>
        <span class="sr-only">{$t('importWizard.notesCount', {values: {n: notes}})}</span>
    </span>
</span>
