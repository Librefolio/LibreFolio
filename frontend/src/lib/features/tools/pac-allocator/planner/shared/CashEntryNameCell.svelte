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

    interface Props {
        broker?: DraftBroker | null;
        currency?: string | null;
        /** `other`: the row of all the cash without a target of its own. */
        other?: boolean;
    }

    let {broker = null, currency = null, other = false}: Props = $props();

    const label = $derived(other ? $t('tools.portfolioRebalancer.planner.targets.otherCash') : $t('tools.portfolioRebalancer.planner.targets.cashEntry', {values: {broker: broker?.name || '—', currency: currency ?? '—'}}));
</script>

<span class="flex min-w-0 items-center gap-2">
    <CashEntryIcon broker={other ? null : broker} currency={other ? null : currency} size={24} />
    <MarqueeName text={label} />
    {#if other}
        <HelpTip {label} help={$t('tools.portfolioRebalancer.planner.targets.otherCashHelp')} />
    {/if}
</span>
