<!--
  FxPairAddModal — Svelte 5

  Modal to add a new FX currency pair with provider configuration.

  Features:
  - CurrencySearchSelect for base and quote currency selection
  - FxProviderSelect for adding compatible providers (auto-add on selection)
  - OrderableList for provider priority with drag & drop
  - Provider section disabled until both currencies are selected
  - Dirty state tracking with ConfirmDialog on close
  - Responsive mobile layout (currencies stack vertically)
  - Full i18n support
  - ModalBase wrapper with proper padding/spacing
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {Trash2, Lock, X, ArrowDown, ArrowRight, Info} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import OrderableList from '$lib/components/ui/OrderableList.svelte';
    import {ConfirmModal} from '$lib/components/table';
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

    // Provider select (for auto-add)
    let newProviderCode = $state('');
    let allProviders = $state<FxProviderInfo[]>([]);

    // Dirty/discard state
    let showDiscardConfirm = $state(false);

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
    let hasProviders = $derived(providerEntries.length > 0);
    let isValid = $derived(hasCurrencies);
    let isDirty = $derived(baseCurrency !== '' || quoteCurrency !== '' || providerEntries.length > 0);

    // =========================================================================
    // Handlers
    // =========================================================================

    function handleProvidersLoaded(providers: FxProviderInfo[]) {
        allProviders = providers;
    }

    /** Auto-add provider when selected from the dropdown */
    function handleProviderSelected(code: string) {
        if (!code) return;
        const provider = allProviders.find(p => p.code === code);
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

        // Reset the select so user can pick another
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
            if (providerEntries.length > 0) {
                // Save with provider sources
                const items = providerEntries.map(p => ({
                    base, quote,
                    provider_code: p.code,
                    priority: p.priority,
                }));
                await zodiosApi.create_pair_sources_bulk_api_v1_fx_providers_pair_sources_post(items);
            }
            // Note: even without providers, the pair is still "created" — the user
            // will need to insert rates manually via the rate edit UI.
            oncreated?.();
            resetAndClose();
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

    /** Try to close — show confirm if dirty */
    function handleClose() {
        if (isDirty) {
            showDiscardConfirm = true;
        } else {
            resetAndClose();
        }
    }

    /** Actually reset and close */
    function resetAndClose() {
        baseCurrency = '';
        quoteCurrency = '';
        providerEntries = [];
        newProviderCode = '';
        error = null;
        showDiscardConfirm = false;
        onclose?.();
    }
</script>

<ModalBase {open} onRequestClose={handleClose} maxWidth="lg" allowOverflow={true}>
    <div class="flex flex-col max-h-[90vh] min-h-[50vh]">
        <!-- ============================================================= -->
        <!-- Header -->
        <!-- ============================================================= -->
        <div class="flex items-center justify-between p-5 pb-4 border-b border-gray-100 dark:border-slate-700 shrink-0">
            <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100">
                {$_('fx.addPair.title')}
            </h2>
            <button
                onclick={handleClose}
                disabled={saving}
                class="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors disabled:opacity-50"
            >
                <X size={20}/>
            </button>
        </div>

        <!-- ============================================================= -->
        <!-- Body (scrollable) -->
        <!-- ============================================================= -->
        <div class="overflow-y-auto flex-1 min-h-0 px-5 py-4 space-y-4">
            <!-- Error banner -->
            {#if error}
                <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-2.5 text-xs text-red-600 dark:text-red-400">
                    {error}
                </div>
            {/if}

            <!-- ========================================================= -->
            <!-- Currency selection -->
            <!-- ========================================================= -->
            <div class="space-y-1.5">
                <div class="flex flex-col sm:flex-row items-stretch sm:items-end gap-2">
                    <div class="flex-1">
                        <div class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                            {$_('fx.addPair.baseCurrency')}
                        </div>
                        <CurrencySearchSelect
                            bind:value={baseCurrency}
                            placeholder={$_('fx.addPair.baseCurrency')}
                            compact={true}
                        />
                    </div>
                    <!-- Arrow: → on desktop, ↓ on mobile -->
                    <span class="text-gray-400 dark:text-gray-500 flex-shrink-0 flex items-center justify-center sm:pb-2">
                        <ArrowRight size={18} class="hidden sm:block" />
                        <ArrowDown size={18} class="sm:hidden" />
                    </span>
                    <div class="flex-1">
                        <div class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                            {$_('fx.addPair.quoteCurrency')}
                        </div>
                        <CurrencySearchSelect
                            bind:value={quoteCurrency}
                            placeholder={$_('fx.addPair.quoteCurrency')}
                            compact={true}
                        />
                    </div>
                </div>
            </div>

            <!-- Info banner: explain provider role -->
            {#if hasCurrencies}
                <div class="flex items-start gap-2 p-2.5 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800/40 rounded-lg text-xs text-blue-700 dark:text-blue-300">
                    <Info size={14} class="flex-shrink-0 mt-0.5" />
                    <span>{$_('fx.addPair.providerInfoBanner')}</span>
                </div>
            {/if}

            <!-- ========================================================= -->
            <!-- Provider Priority -->
            <!-- ========================================================= -->
            <div class="space-y-2 {!hasCurrencies ? 'opacity-50 pointer-events-none' : ''}">
                <h3 class="text-xs font-semibold text-gray-700 dark:text-gray-200 uppercase tracking-wide">
                    {$_('fx.addPair.providerPriority')}
                </h3>

                <!-- Hint when currencies not selected -->
                {#if !hasCurrencies}
                    <div class="flex items-center gap-2 p-2.5 bg-gray-50 dark:bg-slate-700/30 rounded-lg border border-dashed border-gray-300 dark:border-slate-600 text-xs text-gray-400 dark:text-gray-500">
                        <Lock size={12} />
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
                            <div class="flex items-center gap-2 group">
                                <!-- Provider icon -->
                                {#if item.icon_url}
                                    <img
                                        src={item.icon_url}
                                        alt={item.code}
                                        class="w-6 h-6 rounded-md object-contain bg-gray-50 dark:bg-slate-700 p-0.5 flex-shrink-0"
                                    />
                                {:else}
                                    <span class="w-6 h-6 flex items-center justify-center rounded-md bg-libre-green/15 text-libre-green text-[10px] font-bold flex-shrink-0">
                                        {getInitials(item.code)}
                                    </span>
                                {/if}

                                <!-- Provider info -->
                                <div class="flex-1 min-w-0">
                                    <span class="font-medium text-xs text-gray-700 dark:text-gray-200 truncate">
                                        {item.name}
                                    </span>
                                    <span class="text-[10px] text-gray-400 dark:text-gray-500 ml-1">({item.code})</span>
                                </div>

                                <!-- Priority badge -->
                                <span class="text-[10px] font-mono px-1.5 py-0.5 rounded flex-shrink-0
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

                <!-- Add provider (auto-add on selection, no separate + button) -->
                {#if hasCurrencies}
                    <FxProviderSelect
                        bind:value={newProviderCode}
                        {baseCurrency}
                        {quoteCurrency}
                        excludeCodes={usedCodes}
                        onProvidersLoaded={handleProvidersLoaded}
                        onchange={handleProviderSelected}
                        placeholder={$_('fx.addPair.addProvider')}
                    />
                {/if}

                <!-- Intermediate Route placeholder -->
                <div class="p-2.5 bg-gray-50 dark:bg-slate-700/30 rounded-lg border border-dashed border-gray-300 dark:border-slate-600">
                    <div class="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500">
                        <Lock size={12} />
                        <span>{$_('fx.addPair.intermediateRouteComingSoon')}</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- ============================================================= -->
        <!-- No-provider warning -->
        <!-- ============================================================= -->
        {#if hasCurrencies && !hasProviders}
            <div class="flex items-start gap-2 mx-5 mb-0 mt-2 p-2.5 bg-amber-50 dark:bg-amber-900/20 border border-amber-300 dark:border-amber-700/40 rounded-lg text-xs text-amber-700 dark:text-amber-300">
                <Info size={14} class="flex-shrink-0 mt-0.5" />
                <span>{$_('fx.addPair.noProviderWarning')}</span>
            </div>
        {/if}

        <!-- ============================================================= -->
        <!-- Footer -->
        <!-- ============================================================= -->
        <div class="flex justify-end gap-2 px-5 py-3 border-t border-gray-100 dark:border-slate-700 shrink-0">
            <button
                type="button"
                class="px-3 py-1.5 text-sm bg-gray-200 dark:bg-slate-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-slate-500 transition-colors"
                onclick={handleClose}
                disabled={saving}
            >
                {$_('common.cancel')}
            </button>
            <button
                type="button"
                class="px-3 py-1.5 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                onclick={handleSave}
                disabled={!isValid || saving}
            >
                {saving ? $_('common.saving') : $_('fx.addPair.saveConfiguration')}
            </button>
        </div>
    </div>
</ModalBase>

<!-- Discard changes confirmation -->
<ConfirmModal
    open={showDiscardConfirm}
    title={$_('common.discardChanges')}
    message={$_('common.discardChangesMessage')}
    confirmText={$_('common.discard')}
    danger={false}
    warning={true}
    onConfirm={resetAndClose}
    onCancel={() => { showDiscardConfirm = false; }}
    zIndex={70}
/>
