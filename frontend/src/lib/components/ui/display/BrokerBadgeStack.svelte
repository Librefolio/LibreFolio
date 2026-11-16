<!--
  BrokerBadgeStack — the brokers a row stands for, as their icons side by side, slightly overlapped (project 74, «Globale»).

  Each icon is a `BrokerBadge` without its name (the same icon chain); past `max` a «+N» says how many more. One design-system
  tooltip names them all, and so does the accessible label. With `showCount` a short «N brokers» follows the icons.

  Svelte 5 runes, colour roles. Always use `data-testid`.
-->
<script lang="ts">
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import BrokerBadge from '$lib/components/ui/display/BrokerBadge.svelte';
    import {brokerStoreVersion, getBrokerInfo} from '$lib/stores/reference/brokerStore';
    import type {BrokerLike} from '$lib/utils/broker/brokerColors';

    interface Props {
        /** The brokers, in the order to draw them. */
        brokers: ReadonlyArray<BrokerLike>;
        /** Icon size in pixels (default: 16). */
        size?: number;
        /** Icons drawn before «+N» (default: 3). */
        max?: number;
        /** The text after the icons, e.g. «2 brokers»; none: icons only. */
        countLabel?: string | null;
        testId?: string;
    }

    let {brokers, size = 16, max = 3, countLabel = null, testId = 'broker-badge-stack'}: Props = $props();

    let names = $derived.by(() => {
        void $brokerStoreVersion;
        return brokers.map((broker) => broker.name ?? getBrokerInfo(broker.id)?.name ?? `#${broker.id}`);
    });
    let shown = $derived(brokers.slice(0, max));
    let hidden = $derived(Math.max(0, brokers.length - max));
</script>

<Tooltip text={names.join(' · ')} position="top">
    <span class="inline-flex min-w-0 items-center gap-1.5 text-lf-primary" data-testid={testId} data-count={brokers.length} aria-label={names.join(', ')}>
        <span class="inline-flex items-center">
            {#each shown as broker, index (broker.id)}
                <span class="inline-flex rounded-full bg-lf-card ring-2 ring-lf-card {index > 0 ? '-ml-1.5' : ''}">
                    <BrokerBadge {broker} {size} showName={false} />
                </span>
            {/each}
            {#if hidden > 0}
                <span class="-ml-1.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full border border-lf-raised bg-lf-panel px-1 text-[10px] font-semibold text-lf-secondary" data-testid="{testId}-more">+{hidden}</span>
            {/if}
        </span>
        {#if countLabel}
            <span class="truncate text-xs text-lf-muted" data-testid="{testId}-count">{countLabel}</span>
        {/if}
    </span>
</Tooltip>
