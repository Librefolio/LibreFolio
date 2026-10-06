<script lang="ts">
    import {RefreshCw} from 'lucide-svelte';
    import {t, locale} from '$lib/i18n';
    import type {RefreshSummary} from '../copies';
    import {formatCopyStamp} from '../format';
    import {BADGE, NOTICE} from '../ui';
    const KEY = 'tools.pacAllocator.planner.refresh.notice';

    interface Props {
        summary: RefreshSummary;
        asOf: string;
        testid?: string;
    }

    let {summary, asOf, testid = 'pac-planner-refresh-notice'}: Props = $props();

    const stamp = $derived(formatCopyStamp(asOf, summary.readAt, $locale));
    /** Counts and names only: no amount is shown here. */
    const changes = $derived.by(() => {
        const parts = [
            summary.prices > 0 ? $t(`${KEY}.prices`, {default: '{count, plural, one {# price updated} other {# prices updated}}', values: {count: summary.prices}}) : null,
            summary.fx > 0 ? $t(`${KEY}.fx`, {default: '{count, plural, one {# FX rate updated} other {# FX rates updated}}', values: {count: summary.fx}}) : null,
            summary.cash > 0 ? $t(`${KEY}.cash`, {default: '{count, plural, one {# balance updated} other {# balances updated}}', values: {count: summary.cash}}) : null,
        ].filter((part): part is string => part !== null);
        return parts.length > 0 ? parts.join(' · ') : $t(`${KEY}.unchanged`, {default: 'no value changed'});
    });
</script>

<div
    class={summary.missing.length > 0 ? NOTICE.warning : NOTICE.info}
    role="status"
    data-testid={testid}
    data-prices={summary.prices}
    data-fx={summary.fx}
    data-cash={summary.cash}
    data-unchanged={summary.unchanged}
    data-missing={summary.missing.length}
>
    <p class="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span class={BADGE.neutral} data-testid="{testid}-stamp"><RefreshCw size={12} aria-hidden="true" />{stamp}</span>
        <span>{$t(`${KEY}.summary`, {default: 'Copied data read again from LibreFolio: {changes}.', values: {changes}})}</span>
    </p>
    {#if summary.missing.length > 0}
        <p class="mt-1" data-testid="{testid}-missing">{$t(`${KEY}.missing`, {default: 'Not found, the copied value stays: {names}.', values: {names: summary.missing.join(', ')}})}</p>
    {/if}
</div>
