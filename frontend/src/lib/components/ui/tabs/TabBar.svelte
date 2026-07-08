<script lang="ts">
    import type {ComponentType} from 'svelte';

    export interface TabItem {
        id: string;
        label: string;
        icon?: ComponentType | null;
        badge?: number;
        testId?: string;
        className?: string;
    }

    interface Props {
        tabs: TabItem[];
        activeTab?: string;
        onchange?: (id: string) => void;
        class?: string;
        hideLabelOnMobile?: boolean;
        /** Explicit label-visibility override (e.g. container-width driven, from PageToolbar).
         *  undefined (default) falls back to the existing hideLabelOnMobile/`sm:` viewport behavior. */
        showLabels?: boolean;
        /** When true, tabs always stretch to fill 100% of the available width (equal share each),
         *  at every breakpoint — not just below `sm:`. Default false preserves today's behavior
         *  (natural content width above `sm:`), needed e.g. by settings/+page.svelte which relies
         *  on tabs NOT filling full width to push its "admin" tab to the right via `sm:ml-auto`. */
        fillWidth?: boolean;
    }

    let {tabs, activeTab = $bindable(''), onchange, class: className = '', hideLabelOnMobile = false, showLabels, fillWidth = false}: Props = $props();

    function handleTabClick(tabId: string) {
        activeTab = tabId;
        onchange?.(tabId);
    }
</script>

<div class={`flex border-b border-gray-200 dark:border-slate-600 ${className}`.trim()} role="tablist">
    {#each tabs as tab (tab.id)}
        <button
            type="button"
            class={`flex items-center justify-center gap-2 px-3 py-4 sm:px-6 text-sm font-medium transition-all ${fillWidth ? 'flex-1' : 'flex-1 sm:flex-none'} border-b-2 -mb-px ${
                activeTab === tab.id
                    ? 'text-libre-green border-libre-green bg-libre-green/5 dark:text-emerald-400 dark:border-emerald-400 dark:bg-emerald-500/10'
                    : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-800/50 hover:border-gray-300 dark:hover:border-slate-500'
            } ${tab.className ?? ''}`.trim()}
            data-testid={tab.testId ?? `tab-${tab.id}`}
            role="tab"
            aria-selected={activeTab === tab.id}
            title={tab.label}
            onclick={() => handleTabClick(tab.id)}
        >
            {#if tab.icon}
                <tab.icon size={18} />
            {/if}
            <span class={showLabels === false ? 'hidden' : showLabels === true ? '' : hideLabelOnMobile ? 'hidden sm:inline' : ''}>{tab.label}</span>
            {#if tab.badge != null && tab.badge > 0}
                <span class="text-[10px] px-1.5 py-0.5 bg-amber-100 dark:bg-amber-900/40 text-amber-600 dark:text-amber-400 rounded-full">
                    {tab.badge}
                </span>
            {/if}
        </button>
    {/each}
</div>
