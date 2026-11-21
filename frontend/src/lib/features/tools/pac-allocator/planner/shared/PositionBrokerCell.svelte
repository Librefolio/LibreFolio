<!--
  A position's Broker (the Rebalancer's positions, R1-D of project 67): the name, and on a shared account the user's share
  as the Broker page's badge, with the role's icon. A whole account (share 1) shows the name alone.
-->
<script lang="ts">
    import BrokerQuotaBadge from '$lib/features/brokers/BrokerQuotaBadge.svelte';
    import {getPlannerProfile, testId} from '../profile';

    interface Props {
        name: string;
        positionKey: string;
        /** The user's role on the account; null when the copy did not say. */
        role: string | null;
        /** The share as shown («40,00%»), null for a whole account. */
        share: string | null;
        /** The share in words, the badge's hover text. */
        shareTitle: string;
    }

    let {name, positionKey, role, share, shareTitle}: Props = $props();

    /** Read once, while the component is created: the Tool's profile. */
    const profile = getPlannerProfile();
</script>

<span class="flex min-w-0 max-w-full flex-wrap items-center gap-2">
    <span class="min-w-0 max-w-full truncate" title={name}>{name}</span>
    {#if share !== null}
        <BrokerQuotaBadge {role} {share} size={12} title={shareTitle} testid={testId('position-quota', profile)} data-position-key={positionKey} />
    {/if}
</span>
