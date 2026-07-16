<!--
  AiExportMenu — shared "Brain" trigger + dropdown for the AI export catalog.

  Used identically by dashboard, broker detail, and asset detail (Signals panel
  header) so the trigger/positioning/outside-click behavior never drifts between
  the three call sites. Callers translate the catalog entries and pass plain
  {id, label, description, icon} — this component has no i18n or catalog knowledge.
-->
<script lang="ts">
    import {onMount, tick, type ComponentType} from 'svelte';
    import {Brain, RefreshCw} from 'lucide-svelte';
    import {getFixedDropdownPosition} from '$lib/utils/layout/dropdownPosition';

    export interface AiExportMenuEntry {
        id: string;
        label: string;
        description?: string;
        /** Per-entry icon (Lucide component) shown in the dropdown row — falls back to Brain when omitted. */
        icon?: ComponentType;
    }

    interface Props {
        entries: AiExportMenuEntry[];
        loading?: boolean;
        triggerLabel: string;
        loadingLabel: string;
        /** 'end' (default) aligns the panel's right edge with the trigger — matches the existing dashboard/broker-detail placement. */
        align?: 'start' | 'end';
        /** Hide the text label next to the icon (narrow layouts / icon-only placements). */
        showLabel?: boolean;
        onselect: (id: string) => void;
    }

    let {entries, loading = false, triggerLabel, loadingLabel, align = 'end', showLabel = true, onselect}: Props = $props();

    let open = $state(false);
    let triggerEl = $state<HTMLElement | null>(null);
    let panelEl = $state<HTMLDivElement | null>(null);
    let position = $state({left: 8, top: 8});

    async function reposition() {
        await tick();
        if (!open) return;
        position = getFixedDropdownPosition(triggerEl, panelEl, align);
    }

    function toggle() {
        open = !open;
        if (open) void reposition();
    }

    function select(id: string) {
        open = false;
        onselect(id);
    }

    function handleDocumentClick(e: MouseEvent) {
        if (!open) return;
        const target = e.target as HTMLElement;
        if (target.closest?.('[data-ai-export-panel]') || target.closest?.('[data-testid="ai-export-button"]')) return;
        open = false;
    }

    $effect(() => {
        if (!open) return;
        void reposition();
    });

    $effect(() => {
        if (!open) return;
        const handleViewportChange = () => void reposition();
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

<div class="relative w-full">
    <button
        bind:this={triggerEl}
        class="flex items-center justify-center gap-2 w-full px-3 py-1.5 bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg text-xs font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-600 transition-colors disabled:opacity-50"
        onclick={toggle}
        disabled={loading}
        data-testid="ai-export-button"
        title={loading ? loadingLabel : triggerLabel}
    >
        {#if loading}
            <RefreshCw size={14} class="animate-spin" />
        {:else}
            <Brain size={14} />
        {/if}
        {#if showLabel}
            <span>{triggerLabel}</span>
        {/if}
    </button>

    {#if open}
        <div bind:this={panelEl} class="fixed z-50 w-96 max-w-[calc(100vw-1rem)] bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg shadow-lg overflow-hidden" style:left="{position.left}px" style:top="{position.top}px" data-ai-export-panel>
            {#each entries as entry, i (entry.id)}
                <button
                    type="button"
                    class="flex flex-col items-start gap-0.5 w-full px-3 py-2.5 text-left transition-colors hover:bg-gray-50 dark:hover:bg-slate-700 {i > 0 ? 'border-t border-gray-100 dark:border-slate-700' : ''}"
                    onclick={() => select(entry.id)}
                    data-testid={`ai-export-${entry.id}`}
                >
                    <span class="flex items-center gap-2 text-[13px] font-medium text-gray-700 dark:text-gray-200">
                        {#if entry.icon}
                            <entry.icon size={14} class="text-purple-500 shrink-0" />
                        {:else}
                            <Brain size={14} class="text-purple-500 shrink-0" />
                        {/if}
                        {entry.label}
                    </span>
                    {#if entry.description}
                        <span class="text-[11px] text-gray-400 dark:text-gray-500">{entry.description}</span>
                    {/if}
                </button>
            {/each}
        </div>
    {/if}
</div>
