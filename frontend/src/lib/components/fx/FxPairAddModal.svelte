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
    import {Trash2, Lock, X, ArrowDown, ArrowRight, RotateCcw} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import InfoBanner from '$lib/components/ui/InfoBanner.svelte';
    import OrderableList from '$lib/components/ui/OrderableList.svelte';
    import {ConfirmModal} from '$lib/components/table';
    import {CurrencySearchSelect, FxProviderSelect} from '$lib/components/ui/select';
    import type {FxProviderInfo} from '$lib/components/ui/select/FxProviderSelect.svelte';

    // =========================================================================
    // Props (Svelte 5)
    // =========================================================================

    interface Props {
        open?: boolean;
        /** Current date range for auto-sync after creation */
        dateStart?: string;
        dateEnd?: string;
        oncreated?: (detail: {base: string; quote: string; hasRealProvider: boolean}) => void;
        onclose?: () => void;
    }

    let {
        open = $bindable(false),
        dateStart = '',
        dateEnd = '',
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
    let syncing = $state(false);
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
                // Save with provider routes (chain_steps format)
                const items = providerEntries.map(p => ({
                    base, quote,
                    chain_steps: [{from: base, to: quote, provider: p.code}],
                    priority: p.priority,
                }));
                await zodiosApi.create_routes_bulk_api_v1_fx_providers_routes_post(items);
            } else {
                // No providers — create MANUAL sentinel so the pair exists
                // in routes and appears in the list. The backend auto-manages
                // MANUAL: removes it when a real provider is added, reinstates when removed.
                await zodiosApi.create_routes_bulk_api_v1_fx_providers_routes_post([{
                    base, quote,
                    chain_steps: [{from: base, to: quote, provider: 'MANUAL'}],
                    priority: 999,
                }]);
            }
            // Auto-sync if real providers exist (not MANUAL-only)
            const hasRealProvider = providerEntries.length > 0;
            if (hasRealProvider && dateStart && dateEnd) {
                syncing = true;
                try {
                    const slug = base < quote ? `${base}-${quote}` : `${quote}-${base}`;
                    await zodiosApi.sync_rates_api_v1_fx_currencies_sync_post({
                        pairs: [slug],
                        start: dateStart,
                        end: dateEnd,
                    });
                } catch (e) {
                    console.warn('Auto-sync after pair creation failed:', e);
                } finally {
                    syncing = false;
                }
            }

            oncreated?.({
                base, quote,
                hasRealProvider,
            });
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
                <InfoBanner variant="error">{error}</InfoBanner>
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
                        />
                    </div>
                </div>
            </div>

            <!-- Info banner: explain provider role (always visible) -->
            <InfoBanner variant="info">
                {$_('fx.addPair.providerInfoBanner')}
            </InfoBanner>

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
            <div class="mx-5 mb-0 mt-2">
                <InfoBanner variant="warning">
                    {$_('fx.addPair.noProviderWarning')}
                </InfoBanner>
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
                disabled={saving || syncing}
            >
                {$_('common.cancel')}
            </button>
            <button
                type="button"
                class="px-3 py-1.5 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
                onclick={handleSave}
                disabled={!isValid || saving || syncing}
            >
                {#if syncing}
                    <RotateCcw size={14} class="animate-spin" />
                    {$_('fx.actions.syncing')}
                {:else if saving}
                    {$_('common.saving')}
                {:else}
                    {$_('fx.addPair.saveConfiguration')}
                {/if}
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
