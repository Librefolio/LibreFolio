<!--
  FxProviderConfig — Provider/Route configuration panel for a currency pair.

  Shows the list of configured routes with priority badges,
  allows add/delete/reorder via OrderableList, and has save/cancel when changed.
  Supports both 1-step (direct) and multi-step (chain) routes with visual distinction.
-->
<script lang="ts">
    import {Plus, Trash2, Save, Undo2, Link, ArrowLeftRight, Info, AlertTriangle} from 'lucide-svelte';
    import OrderableList from '$lib/components/ui/OrderableList.svelte';
    import Tooltip from '$lib/components/ui/Tooltip.svelte';
    import {getProviderColor, getPriorityBadgeStyle} from '$lib/utils/colors';
    import {getCachedProviders} from '$lib/stores/currencyGraphStore';
    import {_ as t} from '$lib/i18n';

    // =========================================================================
    // Types
    // =========================================================================

    interface ChainStep {
        from: string;
        to: string;
        provider: string;
    }

    interface ProviderEntry {
        providerCode: string;
        priority: number;
        /** Full chain steps — 1 step = direct, 2+ = chain */
        chainSteps?: ChainStep[];
    }

    interface AvailableProvider {
        code: string;
        name: string;
    }

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        providers?: ProviderEntry[];
        availableProviders?: AvailableProvider[];
        readonly?: boolean;
        language?: string;
        onSave?: (providers: ProviderEntry[]) => void;
        onAddProvider?: (detail: {providerCode: string; priority: number}) => void;
        onRemoveProvider?: (detail: {providerCode: string}) => void;
    }

    let {
        providers = $bindable([]),
        availableProviders = [],
        readonly: isReadonly = false,
        language = 'en',
        onSave,
        onAddProvider,
        onRemoveProvider,
    }: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let addingProvider = $state(false);
    let newProviderCode = $state('');
    let hasChanges = $state(false);
    let originalOrder: string[] = $state([]);

    // Track original order for change detection
    $effect(() => {
        originalOrder = providers.map(p => p.providerCode);
        hasChanges = false;
    });

    // =========================================================================
    // Derived
    // =========================================================================

    let usedCodes = $derived(new Set(providers.map(p => p.providerCode)));
    let unusedProviders = $derived(availableProviders.filter(p => !usedCodes.has(p.code)));
    let hasChainRoutes = $derived(providers.some(p => p.chainSteps && p.chainSteps.length > 1));

    // =========================================================================
    // Handlers
    // =========================================================================

    function handleReorder(newItems: ProviderEntry[]) {
        // Update priorities based on new order
        providers = newItems.map((item, idx) => ({
            ...item,
            priority: idx + 1,
        }));
        // Detect if order changed
        const currentOrder = providers.map(p => p.providerCode);
        hasChanges = JSON.stringify(currentOrder) !== JSON.stringify(originalOrder);
    }

    function handleAdd() {
        if (!newProviderCode) return;
        const nextPriority = providers.length > 0 ? Math.max(...providers.map(p => p.priority)) + 1 : 1;
        onAddProvider?.({providerCode: newProviderCode, priority: nextPriority});
        newProviderCode = '';
        addingProvider = false;
    }

    function handleRemove(code: string) {
        onRemoveProvider?.({providerCode: code});
    }

    function handleSave() {
        onSave?.(providers);
        originalOrder = providers.map(p => p.providerCode);
        hasChanges = false;
    }

    function handleRevert() {
        // Re-sort providers back to original order
        const orderMap = new Map(originalOrder.map((code, idx) => [code, idx]));
        providers = [...providers].sort((a, b) =>
            (orderMap.get(a.providerCode) ?? 999) - (orderMap.get(b.providerCode) ?? 999)
        ).map((p, idx) => ({...p, priority: idx + 1}));
        hasChanges = false;
    }

    function getProviderName(code: string): string {
        return availableProviders.find(p => p.code === code)?.name || code;
    }

    function providerKey(prov: ProviderEntry): string {
        return prov.providerCode;
    }

    // Provider info from currencyGraphStore cache (for tooltips)
    let providerInfoMap = $derived(new Map(getCachedProviders().map(p => [p.code, p])));

    function getProviderDescription(code: string): string {
        const prov = providerInfoMap.get(code);
        if (!prov) return '';
        if (prov.description_i18n && Object.keys(prov.description_i18n).length > 0) {
            return prov.description_i18n[language] ?? prov.description_i18n['en'] ?? prov.description ?? '';
        }
        return prov.description ?? '';
    }

    function getProviderFullName(code: string): string {
        return providerInfoMap.get(code)?.name ?? code;
    }

    /** Get provider warning for the current language, with 'en' fallback. */
    function getProviderWarning(code: string): string {
        const prov = providerInfoMap.get(code);
        if (!prov?.warning_i18n || Object.keys(prov.warning_i18n).length === 0) return '';
        return prov.warning_i18n[language] ?? prov.warning_i18n['en'] ?? '';
    }

    /** Collect all unique provider warnings for a route's chain steps. */
    function getItemWarnings(item: ProviderEntry): string[] {
        if (!item.chainSteps) return [];
        const seen = new Set<string>();
        const warnings: string[] = [];
        for (const step of item.chainSteps) {
            if (seen.has(step.provider)) continue;
            seen.add(step.provider);
            const w = getProviderWarning(step.provider);
            if (w) warnings.push(`${getProviderFullName(step.provider)}: ${w}`);
        }
        return warnings;
    }

    // =========================================================================
    // Tooltip HTML builders
    // =========================================================================

    /** Escape HTML entities for safe tooltip content */
    function esc(s: string): string {
        return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    /** Build HTML tooltip for a provider badge */
    function providerTooltipHtml(code: string): string {
        return `<strong>${esc(getProviderFullName(code))}</strong><br/>${esc(getProviderDescription(code))}`;
    }

    /** Build HTML tooltip for warning messages list */
    function warningsTooltipHtml(warnings: string[]): string {
        return warnings.map(w => esc(w)).join('<br/><br/>');
    }
</script>

<div class="space-y-3">
    <div class="flex items-center justify-between">
        <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-200 flex items-center gap-1.5">
            Provider Configuration
            {#if hasChainRoutes}
                <Tooltip text={$t('fx.route.chainWarning')} position="top">
                    <Info size={12} class="text-blue-400 dark:text-blue-500" />
                </Tooltip>
            {/if}
        </h3>
        <div class="flex items-center gap-2">
            {#if hasChanges && !isReadonly}
                <button
                    class="flex items-center gap-1 text-xs px-2 py-1 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors"
                    onclick={handleSave}
                >
                    <Save size={12} />
                    Save Order
                </button>
                <button
                    class="flex items-center gap-1 text-xs px-2 py-1 bg-gray-200 dark:bg-slate-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-slate-500 transition-colors"
                    onclick={handleRevert}
                >
                    <Undo2 size={12} />
                    Revert
                </button>
            {/if}
            {#if !isReadonly && unusedProviders.length > 0}
                <button
                    class="flex items-center gap-1 text-xs text-libre-green hover:text-libre-green/80 transition-colors"
                    onclick={() => addingProvider = !addingProvider}
                >
                    <Plus size={14} />
                    Add Provider
                </button>
            {/if}
        </div>
    </div>

    <!-- Provider list (orderable) -->
    {#if providers.length === 0}
        <p class="text-sm text-gray-400 dark:text-gray-500 py-2">No providers configured for this pair.</p>
    {:else}
        <OrderableList
            items={providers}
            keyFn={providerKey}
            onReorder={handleReorder}
            disabled={isReadonly}
        >
            {#snippet children({ item, index })}
                <div class="flex items-center gap-2">
                    {#if item.chainSteps && item.chainSteps.length > 1}
                        <!-- Multi-step (chain) route -->
                        <Link size={12} class="text-blue-500 dark:text-blue-400 flex-shrink-0" />
                        <div class="flex items-center gap-0.5 flex-wrap flex-1 min-w-0">
                            {#each item.chainSteps as step, i}
                                {@const provColor = getProviderColor(step.provider)}
                                {#if i === 0}
                                    <span class="font-medium text-xs text-gray-600 dark:text-gray-300">{step.from}</span>
                                {/if}
                                <Tooltip html={providerTooltipHtml(step.provider)} position="top">
                                    <span class="inline-flex items-center gap-0.5 px-0.5 py-0.5 rounded border flex-shrink-0"
                                          style="background: {provColor.bg}; border-color: {provColor.border}">
                                        <ArrowLeftRight size={8} class="text-gray-400 dark:text-gray-500 flex-shrink-0" />
                                        <span class="text-[9px] font-mono px-0.5 font-bold flex-shrink-0">
                                            {step.provider}
                                        </span>
                                        <ArrowLeftRight size={8} class="text-gray-400 dark:text-gray-500 flex-shrink-0" />
                                    </span>
                                </Tooltip>
                                <span class="font-medium text-xs text-gray-600 dark:text-gray-300">{step.to}</span>
                            {/each}
                        </div>
                    {:else if item.chainSteps && item.chainSteps.length === 1}
                        <!-- 1-step (direct) route with arrows -->
                        {@const step = item.chainSteps[0]}
                        {@const provColor = getProviderColor(step.provider)}
                        <div class="flex items-center gap-1 flex-1 min-w-0">
                            <span class="font-medium text-xs text-gray-600 dark:text-gray-300">{step.from}</span>
                            <Tooltip html={providerTooltipHtml(step.provider)} position="top">
                                <span class="inline-flex items-center gap-0.5 px-0.5 py-0.5 rounded border flex-shrink-0"
                                      style="background: {provColor.bg}; border-color: {provColor.border}">
                                    <ArrowLeftRight size={8} class="text-gray-400 dark:text-gray-500 flex-shrink-0" />
                                    <span class="text-[9px] font-mono px-0.5 font-bold flex-shrink-0">
                                        {step.provider}
                                    </span>
                                    <ArrowLeftRight size={8} class="text-gray-400 dark:text-gray-500 flex-shrink-0" />
                                </span>
                            </Tooltip>
                            <span class="font-medium text-xs text-gray-600 dark:text-gray-300">{step.to}</span>
                        </div>
                    {:else}
                        <!-- Legacy: no chain steps -->
                        <span class="font-medium text-sm text-gray-700 dark:text-gray-200 truncate">
                            {getProviderName(item.providerCode)}
                        </span>
                    {/if}
                    <span class="text-xs font-mono px-2 py-0.5 rounded flex-shrink-0 priority-badge"
                          style={getPriorityBadgeStyle(index)}>
                        #{index + 1}
                    </span>
                    {#if getItemWarnings(item).length > 0}
                        <Tooltip html={warningsTooltipHtml(getItemWarnings(item))} position="top">
                            <AlertTriangle size={13} class="text-amber-500" />
                        </Tooltip>
                    {/if}
                    {#if !isReadonly}
                        <button
                            class="p-1 rounded-md opacity-0 group-hover:opacity-100 hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-400 hover:text-red-500 transition-all ml-auto"
                            onclick={() => handleRemove(item.providerCode)}
                            title={$t('fx.removeProvider')}
                        >
                            <Trash2 size={14} />
                        </button>
                    {/if}
                </div>
            {/snippet}
        </OrderableList>
    {/if}

    <!-- Add provider form -->
    {#if addingProvider && !isReadonly}
        <div class="flex items-center gap-2 p-3 bg-blue-50 dark:bg-blue-900/10 rounded-lg border border-blue-200 dark:border-blue-800">
            <select
                bind:value={newProviderCode}
                class="flex-1 text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200 px-2.5 py-1.5 focus:ring-1 focus:ring-libre-green"
            >
                <option value="">Select provider...</option>
                {#each unusedProviders as prov}
                    <option value={prov.code}>{prov.name} ({prov.code})</option>
                {/each}
            </select>
            <button
                class="px-3 py-1.5 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors disabled:opacity-50"
                onclick={handleAdd}
                disabled={!newProviderCode}
            >
                Add
            </button>
            <button
                class="px-3 py-1.5 text-sm bg-gray-200 dark:bg-slate-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-slate-500 transition-colors"
                onclick={() => { addingProvider = false; newProviderCode = ''; }}
            >
                Cancel
            </button>
        </div>
    {/if}
</div>

<style>
    .priority-badge {
        background-color: var(--badge-bg);
        color: var(--badge-text);
    }
    :global(.dark) .priority-badge {
        background-color: var(--badge-dark-bg);
        color: var(--badge-dark-text);
    }
</style>
