<script lang="ts">
    import type {ComponentType} from 'svelte';

    interface TabItem {
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
    }

    let {tabs, activeTab = $bindable(''), onchange, class: className = '', hideLabelOnMobile = false}: Props = $props();

    function handleTabClick(tabId: string) {
        activeTab = tabId;
        onchange?.(tabId);
    }
</script>

<div class={`flex border-b border-gray-200 dark:border-slate-600 ${className}`.trim()} role="tablist">
    {#each tabs as tab (tab.id)}
        <button
            type="button"
            class={`flex items-center justify-center gap-2 px-3 py-4 sm:px-6 text-sm font-medium transition-all flex-1 sm:flex-none border-b-2 -mb-px ${
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
            <span class={hideLabelOnMobile ? 'hidden sm:inline' : ''}>{tab.label}</span>
            {#if tab.badge != null && tab.badge > 0}
                <span class="text-[10px] px-1.5 py-0.5 bg-amber-100 dark:bg-amber-900/40 text-amber-600 dark:text-amber-400 rounded-full">
                    {tab.badge}
                </span>
            {/if}
        </button>
    {/each}
</div>
