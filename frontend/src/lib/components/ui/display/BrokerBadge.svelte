<!--
  BrokerBadge — Reusable inline broker display with icon fallback chain.

  Icon resolution order (single source: BrokerIcon.svelte / brokerIconChain.svelte.ts):
  1. `icon_url` (custom uploaded icon)
  2. `portal_url` → origin + /favicon.ico
  3. `default_import_plugin` → plugin icon (app-hosted, async)
  4. System briefcase icon

  Usage:
    <BrokerBadge broker={brokerObj} brokers={allBrokers} />

  Svelte 5 runes. Always use `data-testid`.
-->
<script lang="ts">
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import BrokerIcon from '$lib/components/brokers/BrokerIcon.svelte';
    import {brokerStoreVersion, getBrokerInfo} from '$lib/stores/reference/brokerStore';
    import type {BrokerLike} from '$lib/utils/broker/brokerColors';
    import {getRoleIcon, getRoleIconColor} from '$lib/utils/broker/brokerRoleHelpers';

    interface Props {
        /** The broker to display */
        broker: BrokerLike;
        /** Full broker list (legacy prop kept for API compatibility). */
        brokers?: ReadonlyArray<BrokerLike>;
        /** Icon size in pixels (default: 16). */
        size?: number | 'sm' | 'md' | 'lg';
        /** Show broker name text (default: true) */
        showName?: boolean;
        /** Show role icon after broker name (default: false) */
        showRole?: boolean;
        /** Broker role — used when showRole is true */
        role?: string | null;
        /** Optional tooltip text/html-free. */
        tooltip?: string | null;
        tooltipPosition?: 'top' | 'bottom' | 'left' | 'right';
        /** Optional extra CSS class on the root span. */
        rootClass?: string;
        /** Optional extra CSS class on the name span. */
        nameClass?: string;
    }

    let {broker, brokers: _brokers = [], size = 16, showName = true, showRole = false, role = null, tooltip = null, tooltipPosition = 'top', rootClass = '', nameClass = ''}: Props = $props();

    let resolvedBroker = $derived.by<BrokerLike>(() => {
        void $brokerStoreVersion;
        const cached = getBrokerInfo(broker.id);
        return {
            id: broker.id,
            name: broker.name ?? cached?.name,
            icon_url: broker.icon_url ?? cached?.icon_url ?? null,
            portal_url: broker.portal_url ?? cached?.portal_url ?? null,
            default_import_plugin: broker.default_import_plugin ?? cached?.default_import_plugin ?? null,
        };
    });

    let name = $derived(resolvedBroker.name ?? `#${broker.id}`);
</script>

{#snippet badgeContent()}
    <span class="broker-badge {rootClass}" data-testid="broker-badge-{broker.id}" title={name}>
        <BrokerIcon brokerId={resolvedBroker.id} iconUrl={resolvedBroker.icon_url ?? null} portalUrl={resolvedBroker.portal_url ?? null} pluginCode={resolvedBroker.default_import_plugin ?? null} altText={name} {size} />
        {#if showName}
            <span class="broker-badge-name {nameClass}">{name}</span>
        {/if}
        {#if showRole && role}
            {@const RoleIcon = getRoleIcon(role)}
            <RoleIcon size={typeof size === 'number' ? Math.round(size * 0.75) : 12} class={getRoleIconColor(role)} />
        {/if}
    </span>
{/snippet}

{#if tooltip}
    <Tooltip text={tooltip} position={tooltipPosition}>
        {@render badgeContent()}
    </Tooltip>
{:else}
    {@render badgeContent()}
{/if}

<style>
    .broker-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        max-width: 100%;
        min-width: 0;
    }

    .broker-badge-name {
        font-size: 0.8125rem;
        color: inherit;
        min-width: 0;
        flex: 1 1 auto;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
</style>
