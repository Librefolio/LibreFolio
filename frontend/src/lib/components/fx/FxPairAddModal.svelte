<!--
  FxPairAddModal — Svelte 5

  Modal to add a new FX currency pair with provider configuration.

  Features:
  - CurrencySearchSelect for base and quote currency selection
  - FxProviderSelect for adding compatible providers
  - OrderableList for provider priority with drag & drop
  - Provider section disabled until both currencies are selected
  - Full i18n support
  - ModalBase wrapper
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {Plus, Trash2, Lock} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import OrderableList from '$lib/components/ui/OrderableList.svelte';
    import {CurrencySearchSelect, FxProviderSelect} from '$lib/components/ui/select';
    import type {FxProviderInfo} from '$lib/components/ui/select/FxProviderSelect.svelte';

    // =========================================================================
    // Props (Svelte 5)
    // =========================================================================

    interface Props {
        open?: boolean;
        oncreated?: () => void;
        onclose?: () => void;
    }

    let {
        open = $bindable(false),
        oncreated,
        onclose,
    }: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let baseCurrency = $state('');
    let quoteCurrency = $state('');
    let providerEntries = $state<ProviderEntry[]>([]);
    let saving = $state(false);
    let error = $state<string | null>(null);

    // Provider select
    let newProviderCode = $state('');
    let allProviders = $state<FxProviderInfo[]>([]);

    // =========================================================================
    // Types
    // =========================================================================

    interface ProviderEntry {
        code: string;
        name: string;
        description: string;
        icon_url: string | null;
        priority: number;
    }

    // =========================================================================
    // Derived
    // =========================================================================

    let hasCurrencies = $derived(!!baseCurrency && !!quoteCurrency && baseCurrency !== quoteCurrency);
    let usedCodes = $derived(providerEntries.map(p => p.code));
    let isValid = $derived(hasCurrencies && providerEntries.length > 0);

    // =========================================================================
    // Handlers
    // =========================================================================

    function handleProvidersLoaded(providers: FxProviderInfo[]) {
        allProviders = providers;
    }

    function addProvider() {
        if (!newProviderCode) return;
        const provider = allProviders.find(p => p.code === newProviderCode);
        if (!provider) return;

        const nextPriority = providerEntries.length > 0
            ? Math.max(...providerEntries.map(p => p.priority)) + 1
            : 1;

        providerEntries = [...providerEntries, {
            code: provider.code,
            name: provider.name,
            description: provider.description,
            icon_url: provider.icon_url,
            priority: nextPriority,
        }];
        newProviderCode = '';
    }

    function removeProvider(code: string) {
        providerEntries = providerEntries
            .filter(p => p.code !== code)
            .map((p, i) => ({...p, priority: i + 1}));
    }

    function handleReorder(newItems: ProviderEntry[]) {
        providerEntries = newItems.map((item, idx) => ({
            ...item,
            priority: idx + 1,
        }));
    }

    function providerKey(prov: ProviderEntry): string {
        return prov.code;
    }

    function getInitials(code: string): string {
        return code.slice(0, 2).toUpperCase();
    }

    async function handleSave() {
        if (!isValid) return;
        saving = true;
        error = null;

        // Normalize alphabetical order for storage
        const base = baseCurrency.toUpperCase() < quoteCurrency.toUpperCase()
            ? baseCurrency.toUpperCase() : quoteCurrency.toUpperCase();
        const quote = baseCurrency.toUpperCase() < quoteCurrency.toUpperCase()
            ? quoteCurrency.toUpperCase() : baseCurrency.toUpperCase();

        try {
            const items = providerEntries.map(p => ({
                base, quote,
                provider_code: p.code,
                priority: p.priority,
            }));
            await zodiosApi.create_pair_sources_bulk_api_v1_fx_providers_pair_sources_post(items);
            oncreated?.();
            handleClose();
        } catch (e: any) {
            const detail = e?.response?.data?.detail;
            if (detail?.message) {
                error = detail.message;
            } else {
                error = e?.message || 'Failed to create pair';
            }
        } finally {
            saving = false;
        }
    }

    function handleClose() {
        baseCurrency = '';
        quoteCurrency = '';
        providerEntries = [];
        newProviderCode = '';
        error = null;
        onclose?.();
    }
</script>

<ModalBase {open} onRequestClose={handleClose} maxWidth="lg">
    <div class="space-y-5">
        <!-- Title -->
        <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100">
            {$_('fx.addPair.title')}
        </h2>

        <!-- Error banner -->
        {#if error}
            <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 text-sm text-red-600 dark:text-red-400">
                {error}
            </div>
        {/if}

        <!-- ============================================================= -->
        <!-- Currency selection -->
        <!-- ============================================================= -->
        <div class="space-y-2">
            <div class="flex items-end gap-3">
                <div class="flex-1">
                    <div class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                        {$_('fx.addPair.baseCurrency')}
                    </div>
                    <CurrencySearchSelect
                        bind:value={baseCurrency}
                        placeholder={$_('fx.addPair.baseCurrency')}
                    />
                </div>
                <span class="text-gray-400 dark:text-gray-500 text-lg pb-2 flex-shrink-0">→</span>
                <div class="flex-1">
                    <div class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                        {$_('fx.addPair.quoteCurrency')}
                    </div>
                    <CurrencySearchSelect
                        bind:value={quoteCurrency}
                        placeholder={$_('fx.addPair.quoteCurrency')}
                    />
                </div>
            </div>
        </div>

        <!-- ============================================================= -->
        <!-- Provider Priority -->
        <!-- ============================================================= -->
        <div class="space-y-3 {!hasCurrencies ? 'opacity-50 pointer-events-none' : ''}">
            <div class="flex items-center justify-between">
                <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-200">
                    {$_('fx.addPair.providerPriority')}
                </h3>
            </div>

            <!-- Hint when currencies not selected -->
            {#if !hasCurrencies}
                <div class="flex items-center gap-2 p-3 bg-gray-50 dark:bg-slate-700/30 rounded-lg border border-dashed border-gray-300 dark:border-slate-600 text-sm text-gray-400 dark:text-gray-500">
                    <Lock size={14} />
                    {$_('fx.addPair.providerDisabledHint')}
                </div>
            {/if}

            <!-- Provider list (orderable) -->
            {#if providerEntries.length > 0}
                <OrderableList
                    items={providerEntries}
                    keyFn={providerKey}
                    onReorder={handleReorder}
                >
                    {#snippet children({ item, index })}
                        <div class="flex items-center gap-2.5 group">
                            <!-- Provider icon -->
                            {#if item.icon_url}
                                <img
                                    src={item.icon_url}
                                    alt={item.code}
                                    class="w-7 h-7 rounded-md object-contain bg-gray-50 dark:bg-slate-700 p-0.5 flex-shrink-0"
                                />
                            {:else}
                                <span class="w-7 h-7 flex items-center justify-center rounded-md bg-libre-green/15 text-libre-green text-xs font-bold flex-shrink-0">
                                    {getInitials(item.code)}
                                </span>
                            {/if}

                            <!-- Provider info -->
                            <div class="flex-1 min-w-0">
                                <span class="font-medium text-sm text-gray-700 dark:text-gray-200 truncate">
                                    {item.name}
                                </span>
                                <span class="text-xs text-gray-400 dark:text-gray-500 ml-1">({item.code})</span>
                            </div>

                            <!-- Priority badge -->
                            <span class="text-xs font-mono px-2 py-0.5 rounded flex-shrink-0
                                {index === 0
                                    ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400'
                                    : 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400'}">
                                #{index + 1} {index === 0 ? $_('fx.provider.primary') : $_('fx.provider.fallback')}
                            </span>

                            <!-- Remove button -->
                            <button
                                type="button"
                                class="p-1 rounded-md text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all flex-shrink-0"
                                onclick={() => removeProvider(item.code)}
                                title="Remove"
                            >
                                <Trash2 size={14} />
                            </button>
                        </div>
                    {/snippet}
                </OrderableList>
            {/if}

            <!-- Add provider -->
            {#if hasCurrencies}
                <div class="flex items-center gap-2">
                    <div class="flex-1">
                        <FxProviderSelect
                            bind:value={newProviderCode}
                            {baseCurrency}
                            {quoteCurrency}
                            excludeCodes={usedCodes}
                            onProvidersLoaded={handleProvidersLoaded}
                            placeholder={$_('fx.addPair.addProvider')}
                        />
                    </div>
                    <button
                        type="button"
                        class="p-2 text-libre-green hover:bg-libre-green/10 rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0"
                        onclick={addProvider}
                        disabled={!newProviderCode}
                        title={$_('fx.addPair.addProvider')}
                    >
                        <Plus size={18} />
                    </button>
                </div>
            {/if}

            <!-- Intermediate Route placeholder -->
            <div class="p-3 bg-gray-50 dark:bg-slate-700/30 rounded-lg border border-dashed border-gray-300 dark:border-slate-600">
                <div class="flex items-center gap-2 text-sm text-gray-400 dark:text-gray-500">
                    <Lock size={14} />
                    <span>{$_('fx.addPair.intermediateRouteComingSoon')}</span>
                </div>
            </div>
        </div>

        <!-- ============================================================= -->
        <!-- Footer -->
        <!-- ============================================================= -->
        <div class="flex justify-end gap-2 pt-3 border-t border-gray-100 dark:border-slate-700">
            <button
                type="button"
                class="px-4 py-2 text-sm bg-gray-200 dark:bg-slate-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-slate-500 transition-colors"
                onclick={handleClose}
            >
                {$_('common.cancel')}
            </button>
            <button
                type="button"
                class="px-4 py-2 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                onclick={handleSave}
                disabled={!isValid || saving}
            >
                {saving ? $_('common.saving') : $_('fx.addPair.saveConfiguration')}
            </button>
        </div>
    </div>
</ModalBase>
