<!--
  The icon of a cash entry (F3a of project 67, M3): the Broker's logo with a small circle in its corner holding the
  currency's symbol, as the composite Asset types do (`utils/assetTypes.ts`, there as images; here in CSS). Without a
  Broker a plain circle with a wallet stands for the cash.
-->
<script lang="ts">
    import {Wallet} from 'lucide-svelte';
    import {currentLanguage} from '$lib/stores/app/language';
    import {currencyStoreVersion, ensureCurrenciesLoaded, getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import type {DraftBroker} from '../draft.svelte';
    import {ICON_BUBBLE} from '../ui';
    import PlannerBrokerIcon from './PlannerBrokerIcon.svelte';

    interface Props {
        broker: DraftBroker | null | undefined;
        currency?: string | null;
        size?: number;
    }

    let {broker, currency = null, size = 24}: Props = $props();

    // Idempotent; until the currency catalogue arrives, or if it fails, the bare code stands for the symbol.
    $effect(() => {
        ensureCurrenciesLoaded($currentLanguage).catch(() => undefined);
    });

    /** The currency's own short symbol from the catalogue (€, $): a label, not an amount. */
    const symbol = $derived.by(() => {
        void $currencyStoreVersion;
        if (!currency) return '';
        const info = getCurrencyInfo(currency);
        return info.symbol && info.symbol.length <= 3 ? info.symbol : currency;
    });
    const badge = $derived(Math.max(12, Math.round(size * 0.55)));
</script>

<span class="relative inline-flex shrink-0" style="width: {size}px; height: {size}px;" data-currency={currency ?? undefined}>
    {#if broker}
        <PlannerBrokerIcon {broker} {size} />
    {:else}
        <span class={ICON_BUBBLE} style="width: {size}px; height: {size}px;"><Wallet size={Math.round(size * 0.55)} aria-hidden="true" /></span>
    {/if}
    {#if symbol}
        <span
            class="absolute -right-1 -bottom-1 inline-flex items-center justify-center overflow-hidden rounded-full border border-lf-subtle bg-lf-card font-semibold leading-none text-lf-primary"
            style="min-width: {badge}px; height: {badge}px; font-size: {Math.round(badge * 0.6)}px; padding: 0 2px;"
            aria-hidden="true">{symbol}</span
        >
    {/if}
</span>
