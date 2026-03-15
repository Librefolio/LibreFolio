<!--
  FxPairAddModal — Svelte 5

  Modal to add a new FX currency pair with route configuration.

  Features:
  - CurrencySearchSelect for base and quote currency selection
  - FxProviderSelect for selecting conversion routes (direct 1-step or chain multi-step)
  - Route selection with DFS pathfinding on currency graph
  - Full-text search across providers, currencies, countries
  - Provider section disabled until both currencies are selected
  - Dirty state tracking with ConfirmDialog on close
  - Responsive mobile layout (currencies stack vertically)
  - Full i18n support
  - ModalBase wrapper with proper padding/spacing
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {Lock, X, ArrowDown, ArrowRight, RotateCcw} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import InfoBanner from '$lib/components/ui/InfoBanner.svelte';
    import {ConfirmModal} from '$lib/components/table';
    import {CurrencySearchSelect, FxProviderSelect} from '$lib/components/ui/select';
    import type {ChainStep} from '$lib/utils/currencyGraph';

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
    let selectedRoutes = $state<ChainStep[][]>([]);
    let saving = $state(false);
    let syncing = $state(false);
    let error = $state<string | null>(null);
    let quoteSelectRef = $state<HTMLDivElement | null>(null);

    // Dirty/discard state
    let showDiscardConfirm = $state(false);

    // =========================================================================
    // Derived
    // =========================================================================

    let hasCurrencies = $derived(!!baseCurrency && !!quoteCurrency && baseCurrency !== quoteCurrency);
    let hasRoutes = $derived(selectedRoutes.length > 0);
    let isValid = $derived(hasCurrencies);
    let isDirty = $derived(baseCurrency !== '' || quoteCurrency !== '' || selectedRoutes.length > 0);

    // =========================================================================
    // Handlers
    // =========================================================================

    function handleRoutesChange(routes: ChainStep[][]) {
        selectedRoutes = routes;
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
            if (selectedRoutes.length > 0) {
                // Save with selected routes (each route has its own chain_steps)
                const items = selectedRoutes.map((chainSteps, idx) => ({
                    base, quote,
                    chain_steps: chainSteps,
                    priority: idx + 1,
                }));
                await zodiosApi.create_routes_bulk_api_v1_fx_providers_routes_post(items);
            } else {
                // No routes selected — create MANUAL sentinel so the pair exists
                // in routes and appears in the list. The backend auto-manages
                // MANUAL: removes it when a real provider is added, reinstates when removed.
                await zodiosApi.create_routes_bulk_api_v1_fx_providers_routes_post([{
                    base, quote,
                    chain_steps: [{from: base, to: quote, provider: 'MANUAL'}],
                    priority: 999,
                }]);
            }
            // Auto-sync if real routes exist (not MANUAL-only)
            const hasRealProvider = selectedRoutes.length > 0;
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
        selectedRoutes = [];
        error = null;
        showDiscardConfirm = false;
        onclose?.();
    }
</script>

<ModalBase {open} onRequestClose={handleClose} maxWidth="lg" allowOverflow={true}>
    <div class="flex flex-col max-h-[90vh] min-h-[50vh]" data-testid="fx-add-pair-modal">
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
                            onchange={() => {
                                // Auto-focus the quote currency select after picking base
                                setTimeout(() => {
                                    const trigger = quoteSelectRef?.querySelector<HTMLElement>('[tabindex], input');
                                    trigger?.focus();
                                    trigger?.click();
                                }, 30);
                            }}
                        />
                    </div>
                    <!-- Arrow: → on desktop, ↓ on mobile -->
                    <span class="text-gray-400 dark:text-gray-500 flex-shrink-0 flex items-center justify-center sm:mt-5">
                        <ArrowRight size={18} class="hidden sm:block" />
                        <ArrowDown size={18} class="sm:hidden" />
                    </span>
                    <div class="flex-1" bind:this={quoteSelectRef}>
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
            <!-- Route Selection (DFS pathfinding) -->
            <!-- ========================================================= -->
            <div class="space-y-2 {!hasCurrencies ? 'opacity-50 pointer-events-none' : ''}">
                <h3 class="text-xs font-semibold text-gray-700 dark:text-gray-200 uppercase tracking-wide">
                    {$_('fx.route.title')}
                </h3>

                <!-- Hint when currencies not selected -->
                {#if !hasCurrencies}
                    <div class="flex items-center gap-2 p-2.5 bg-gray-50 dark:bg-slate-700/30 rounded-lg border border-dashed border-gray-300 dark:border-slate-600 text-xs text-gray-400 dark:text-gray-500">
                        <Lock size={12} />
                        {$_('fx.addPair.providerDisabledHint')}
                    </div>
                {/if}

                <!-- Route selection (unified: DFS pathfinding + search + flags) -->
                <FxProviderSelect
                    {baseCurrency}
                    {quoteCurrency}
                    bind:selectedRoutes
                    onSelectionChange={handleRoutesChange}
                    disabled={!hasCurrencies}
                />
            </div>
        </div>

        <!-- ============================================================= -->
        <!-- No-provider warning -->
        <!-- ============================================================= -->
        {#if hasCurrencies && !hasRoutes}
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
                data-testid="fx-add-pair-save"
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
