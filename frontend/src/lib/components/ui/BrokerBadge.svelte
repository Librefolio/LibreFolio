<!--
  BrokerBadge — Reusable broker display with icon fallback chain.

  Icon resolution order:
  1. `icon_url` (custom uploaded icon)
  2. `portal_url` → origin + /favicon.ico
  3. Colored dot (deterministic broker color)

  When an icon is available, no colored dot/badge is shown.

  Usage:
    <BrokerBadge broker={brokerObj} brokers={allBrokers} />

  Svelte 5 runes. Always use `data-testid`.
-->
<script lang="ts">
    import {getBrokerColor, type BrokerLike} from '$lib/utils/brokerColors';
    import {getBrokerIconUrl} from '$lib/utils/brokerHelpers';
    import {getRoleIcon, getRoleIconColor} from '$lib/utils/brokerRoleHelpers';

    interface Props {
        /** The broker to display */
        broker: BrokerLike;
        /** Full broker list for deterministic color resolution */
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

    let {broker, brokers, size = 16, showName = true, showRole = false, role = null}: Props = $props();

    let iconUrl = $derived(getBrokerIconUrl(broker));

    let color = $derived(getBrokerColor(broker.id, brokers));
    let name = $derived(broker.name ?? `#${broker.id}`);

    let iconFailed = $state(false);
</script>

<span class="broker-badge" data-testid="broker-badge-{broker.id}" title={name}>
    {#if iconUrl && !iconFailed}
        <img src={iconUrl} alt="" class="broker-badge-icon" style="width:{size}px;height:{size}px" onerror={() => (iconFailed = true)} />
    {:else}
        <span class="broker-badge-dot" style="width:{Math.round(size * 0.625)}px;height:{Math.round(size * 0.625)}px;background:{color.bg}"></span>
    {/if}
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

    .broker-badge-icon {
        border-radius: 3px;
        object-fit: contain;
        flex-shrink: 0;
    }

    .broker-badge-dot {
        display: inline-block;
        border-radius: 9999px;
        flex-shrink: 0;
        box-shadow: 0 0 0 1px rgb(0 0 0 / 0.06);
    }

    :global(.dark) .broker-badge-dot {
        box-shadow: 0 0 0 1px rgb(255 255 255 / 0.08);
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
