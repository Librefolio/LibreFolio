<script lang="ts">
    /**
     * The icon of a draft Broker, wherever the planner names one.
     *
     * A copied Broker keeps only `iconUrl` in the draft; portal and plugin come
     * from the Broker store for the usual fallback chain. A manual Broker falls
     * back to the system icon, an external account (funding only) to a bank.
     */
    import {Landmark} from 'lucide-svelte';
    import BrokerIcon from '$lib/components/brokers/BrokerIcon.svelte';
    import {brokerStoreVersion, getBrokerInfo} from '$lib/stores/reference/brokerStore';
    import type {DraftBroker} from '../draft.svelte';
    import {ICON_BUBBLE} from '../ui';

    interface Props {
        broker: DraftBroker | null | undefined;
        size?: number;
    }

    let {broker, size = 28}: Props = $props();

    const info = $derived.by(() => {
        void $brokerStoreVersion;
        return broker?.sourceBrokerId == null ? undefined : getBrokerInfo(broker.sourceBrokerId);
    });
</script>

{#if broker?.fundingOnly}
    <span class={ICON_BUBBLE} style="width: {size}px; height: {size}px;"><Landmark size={Math.round(size * 0.55)} aria-hidden="true" /></span>
{:else if broker}
    <BrokerIcon brokerId={broker.sourceBrokerId} iconUrl={broker.iconUrl ?? info?.icon_url ?? null} portalUrl={info?.portal_url ?? null} pluginCode={info?.default_import_plugin ?? null} altText="" {size} />
{/if}
