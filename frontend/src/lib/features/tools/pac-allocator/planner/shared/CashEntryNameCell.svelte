<!--
  The name cell of a cash row in the targets table (F3a of project 67, M3, M12): the cash icon and «Cash · Broker · EUR»;
  «Other cash» for all the cash without a target of its own, with its help.
-->
<script lang="ts">
    import {t} from '$lib/i18n';
    import type {DraftBroker} from '../draft.svelte';
    import CashEntryIcon from './CashEntryIcon.svelte';
    import HelpTip from './HelpTip.svelte';
    import MarqueeName from './MarqueeName.svelte';
    import NowLine, {type NowLineContent} from './NowLine.svelte';

    interface Props {
        broker?: DraftBroker | null;
        currency?: string | null;
        /** `other`: the row of all the cash without a target of its own. */
        other?: boolean;
        /** «Now» under the name, in the targets table while its column is hidden (G5-1 of project 67). */
        now?: NowLineContent | null;
    }

    let {broker = null, currency = null, other = false, now = null}: Props = $props();

    const label = $derived(other ? $t('tools.portfolioRebalancer.planner.targets.otherCash') : $t('tools.portfolioRebalancer.planner.targets.cashEntry', {values: {broker: broker?.name || '—', currency: currency ?? '—'}}));
</script>

<span class="flex min-w-0 items-center gap-2">
    <CashEntryIcon broker={other ? null : broker} currency={other ? null : currency} size={24} />
    {#if now}
        <!-- The help stays beside the name, «now» goes under both (G5-1). -->
        <span class="flex min-w-0 flex-col">
            <span class="flex min-w-0 items-center gap-2">
                <MarqueeName text={label} />
                {#if other}
                    <HelpTip {label} help={$t('tools.portfolioRebalancer.planner.targets.otherCashHelp')} />
                {/if}
            </span>
            <NowLine {now} />
        </span>
    {:else}
        <MarqueeName text={label} />
        {#if other}
            <HelpTip {label} help={$t('tools.portfolioRebalancer.planner.targets.otherCashHelp')} />
        {/if}
    {/if}
</span>
