<!--
  BrokerFilterSelect — the broker multi-select of the portfolio view's toolbar (Y6-7, delivery 2, checkpoint 9e; moved out of
  `PortfolioView.svelte`, markup and `data-testid`s kept).

  With one broker selected the label is that broker's name, of any length: the trigger shrinks and truncates it instead of
  pushing out of the bar (the full name stays in the DOM). The menu is `fixed`, placed by `getFixedDropdownPosition`, so the
  toolbar's own overflow never clips it; an outside click, a resize or a scroll closes or moves it.

  It owns nothing of the selection: it shows `selectedIds` and tells the view the next set through `onselect`.
-->
<script lang="ts">
    import {onMount, tick} from 'svelte';
    import {_} from '$lib/i18n';
    import BrokerIcon from '$lib/components/ui/display/BrokerIcon.svelte';
    import {getBrokerRole} from '$lib/stores/reference/brokerStore';
    import {getRoleIcon, getRoleIconColor} from '$lib/utils/broker/brokerRoleHelpers';
    import {getFixedDropdownPosition} from '$lib/utils/layout/dropdownPosition';
    import type {BrokerLike} from '$lib/utils/broker/brokerColors';

    interface Props {
        brokers: BrokerLike[];
        selectedIds: number[];
        /** Some but not all brokers are selected: the trigger is highlighted and says which. */
        active: boolean;
        onselect: (ids: number[]) => void;
    }

    let {brokers, selectedIds, active, onselect}: Props = $props();

    let open = $state(false);
    let triggerEl = $state<HTMLButtonElement | null>(null);
    let panelEl = $state<HTMLDivElement | null>(null);
    let position = $state({left: 8, top: 8});

    /** Broker filter trigger label — follows assets-page type-filter pattern (no separate badge). */
    const label = $derived(active ? (selectedIds.length === 1 ? (brokers.find((b) => b.id === selectedIds[0])?.name ?? String(selectedIds[0])) : `${$_('brokers.title')} (${selectedIds.length})`) : $_('dashboard.allBrokers'));

    function toggleBroker(id: number) {
        onselect(selectedIds.includes(id) ? selectedIds.filter((x) => x !== id) : [...selectedIds, id]);
    }

    async function placeMenu() {
        await tick();
        if (!open) return;
        position = getFixedDropdownPosition(triggerEl, panelEl, 'start');
    }

    function toggleMenu() {
        open = !open;
        if (open) void placeMenu();
    }

    // Outside-click closes the broker filter panel (AI export dropdown handles its own outside-click internally)
    function handleDocumentClick(e: MouseEvent) {
        if (!open) return;
        const target = e.target as HTMLElement;
        if (target.closest?.('[data-broker-filter-panel]') || target.closest?.('[data-testid="broker-filter-trigger"]')) return;
        open = false;
    }

    $effect(() => {
        if (!open) return;
        void placeMenu();
    });

    $effect(() => {
        if (!open) return;

        const handleViewportChange = () => {
            if (open) position = getFixedDropdownPosition(triggerEl, panelEl, 'start');
        };
        window.addEventListener('resize', handleViewportChange);
        window.addEventListener('scroll', handleViewportChange, true);

        return () => {
            window.removeEventListener('resize', handleViewportChange);
            window.removeEventListener('scroll', handleViewportChange, true);
        };
    });

    onMount(() => {
        document.addEventListener('click', handleDocumentClick);
        return () => document.removeEventListener('click', handleDocumentClick);
    });
</script>

<div class="relative min-w-0">
    <button
        bind:this={triggerEl}
        class="flex items-center gap-1.5 min-w-0 max-w-full px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors whitespace-nowrap
                       {active ? 'bg-lf-selected text-lf-link border-lf-focus' : 'bg-lf-card text-lf-secondary border-lf-input hover:bg-lf-hover'}"
        onclick={toggleMenu}
        data-testid="broker-filter-trigger"
    >
        <span class="truncate">{label}</span>
        <svg class="w-3 h-3 shrink-0 transition-transform {open ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path d="M19 9l-7 7-7-7" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" />
        </svg>
    </button>

    {#if open}
        <div bind:this={panelEl} class="fixed z-50 w-56 bg-lf-card border border-lf-raised rounded-lg shadow-lg shadow-lf-shadow overflow-hidden" style:left={`${position.left}px`} style:top={`${position.top}px`} data-broker-filter-panel>
            <!-- Select All / Deselect All -->
            <div class="flex gap-2 px-2.5 py-2 border-b border-lf-subtle">
                <button type="button" class="flex-1 px-2 py-1 text-[11px] font-medium border border-lf-subtle rounded bg-lf-panel text-lf-secondary hover:bg-lf-neutral transition-colors" onclick={() => onselect(brokers.map((b) => b.id))}>{$_('common.selectAll')}</button>
                <button type="button" class="flex-1 px-2 py-1 text-[11px] font-medium border border-lf-subtle rounded bg-lf-panel text-lf-secondary hover:bg-lf-neutral transition-colors" onclick={() => onselect([])}>{$_('common.clearAll')}</button>
            </div>
            <!-- Broker list -->
            <div class="max-h-52 overflow-y-auto mx-2.5 my-2 space-y-0.5">
                {#each brokers as broker (broker.id)}
                    {@const isSelected = selectedIds.includes(broker.id)}
                    {@const role = getBrokerRole(broker.id)}
                    {@const RoleIcon = role ? getRoleIcon(role) : null}
                    <button type="button" class="flex items-center gap-2 w-full px-2 py-1.5 text-left text-[13px] rounded hover:bg-lf-hover transition-colors {isSelected ? 'text-lf-link' : 'text-lf-secondary'}" onclick={() => toggleBroker(broker.id)} data-testid="broker-filter-item-{broker.id}">
                        <BrokerIcon brokerId={broker.id} iconUrl={broker.icon_url} portalUrl={broker.portal_url} pluginCode={broker.default_import_plugin} altText={broker.name} size={16} />
                        <span class="flex-1 truncate">{broker.name}</span>
                        {#if RoleIcon}
                            <RoleIcon size={14} class={getRoleIconColor(role)} />
                        {/if}
                        {#if isSelected}
                            <svg class="w-3.5 h-3.5 text-lf-link flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path d="M5 13l4 4L19 7" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" />
                            </svg>
                        {/if}
                    </button>
                {/each}
            </div>
        </div>
    {/if}
</div>
