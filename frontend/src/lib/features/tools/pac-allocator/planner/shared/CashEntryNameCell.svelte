<!--
  The name cell of a cash row in the targets table (F3a of project 67, M3, M12): the cash icon and «Cash · Broker · EUR».
  The cash without a target of its own has no row (TL-2 of project 67): the plan counts it, the table does not show it.
-->
<script lang="ts">
    import {t} from '$lib/i18n';
    import type {DraftBroker} from '../draft.svelte';
    import CashEntryIcon from './CashEntryIcon.svelte';
    import MarqueeName from './MarqueeName.svelte';
    import NowLine, {type NowLineContent} from './NowLine.svelte';

    interface Props {
        broker?: DraftBroker | null;
        currency?: string | null;
        /** «Now» under the name, in the targets table while its column is hidden (G5-1 of project 67). */
        now?: NowLineContent | null;
    }

    let {broker = null, currency = null, now = null}: Props = $props();

    const label = $derived($t('tools.portfolioRebalancer.planner.targets.cashEntry', {values: {broker: broker?.name || '—', currency: currency ?? '—'}}));
</script>

<span class="flex min-w-0 items-center gap-2">
    <CashEntryIcon {broker} {currency} size={24} />
    {#if now}
        <!-- «Now» goes under the name (G5-1). -->
        <span class="flex min-w-0 flex-col">
            <MarqueeName text={label} />
            <NowLine {now} />
        </span>
    {:else}
        <MarqueeName text={label} />
    {/if}
</span>
