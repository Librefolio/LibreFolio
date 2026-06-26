<!--
  BrokerBadge — Reusable inline broker display with icon fallback chain.

  Icon resolution order (matches BrokerIcon — single source: brokerIconChain.svelte.ts):
  1. `icon_url` (custom uploaded icon)
  2. `portal_url` → origin + /favicon.ico
  3. `default_import_plugin` → plugin icon (app-hosted, async)
  4. Initial letter of broker name

  Usage:
    <BrokerBadge broker={brokerObj} brokers={allBrokers} />

  Svelte 5 runes. Always use `data-testid`.
-->
<script lang="ts">
    import type {BrokerLike} from '$lib/utils/broker/brokerColors';
    import {createBrokerIconChain} from '$lib/utils/broker/brokerIconChain.svelte';
    import {getRoleIcon, getRoleIconColor} from '$lib/utils/broker/brokerRoleHelpers';

    interface Props {
        /** The broker to display */
        broker: BrokerLike;
        /** Full broker list (kept for API compatibility — no longer used for color) */
        brokers: ReadonlyArray<BrokerLike>;
        /** Icon size in pixels (default: 16) */
        size?: number;
        /** Show broker name text (default: true) */
        showName?: boolean;
        /** Show role icon after broker name (default: false) */
        showRole?: boolean;
        /** Broker role — used when showRole is true */
        role?: string | null;
    }

    let {broker, brokers: _brokers, size = 16, showName = true, showRole = false, role = null}: Props = $props();

    // Shared reactive fallback chain — same logic as BrokerIcon
    const chain = createBrokerIconChain(() => broker);

    let name = $derived(broker.name ?? `#${broker.id}`);
    let initial = $derived(name.trim().charAt(0).toUpperCase());
</script>

<span class="broker-badge" data-testid="broker-badge-{broker.id}" title={name}>
    <span class="broker-badge-icon-wrap" style="width:{size}px;height:{size}px">
        {#if chain.currentDisplayUrl}
            {#key chain.currentDisplayUrl}
                <img src={chain.currentDisplayUrl} alt="" class="broker-badge-img {chain.imageLoaded ? '' : 'opacity-0'}" onload={chain.handleLoad} onerror={chain.handleError} referrerpolicy="no-referrer" />
            {/key}
        {/if}
        {#if !chain.imageLoaded || !chain.currentDisplayUrl}
            <span class="broker-badge-initial">{initial}</span>
        {/if}
    </span>
    {#if showName}
        <span class="broker-badge-name">{name}</span>
    {/if}
    {#if showRole && role}
        {@const RoleIcon = getRoleIcon(role)}
        <RoleIcon size={Math.round(size * 0.75)} class={getRoleIconColor(role)} />
    {/if}
</span>

<style>
    .broker-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        max-width: 100%;
        min-width: 0;
    }

    .broker-badge-icon-wrap {
        position: relative;
        flex-shrink: 0;
        border-radius: 3px;
        overflow: hidden;
        background: rgb(34 197 94 / 0.1);
        display: flex;
        align-items: center;
        justify-content: center;
    }

    :global(.dark) .broker-badge-icon-wrap {
        background: rgb(34 197 94 / 0.2);
    }

    .broker-badge-img {
        width: 100%;
        height: 100%;
        object-fit: contain;
        transition: opacity 0.15s ease-in-out;
    }

    .broker-badge-initial {
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.6rem;
        font-weight: 700;
        color: #22c55e;
        text-transform: uppercase;
        user-select: none;
        line-height: 1;
    }

    :global(.dark) .broker-badge-initial {
        color: #4ade80;
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
