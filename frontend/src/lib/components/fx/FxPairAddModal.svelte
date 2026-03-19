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
    import {Lock, X, ArrowDownUp, ArrowLeftRight, RotateCcw} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import InfoBanner from '$lib/components/ui/InfoBanner.svelte';
    import {ConfirmModal} from '$lib/components/table';
    import {CurrencySearchSelect, FxProviderSelect} from '$lib/components/ui/select';
    import type {ChainStep} from '$lib/utils/currencyGraph';
    import {getRegisteredPairs} from '$lib/stores/fxStoreRegistry';
    import {currentLanguage} from '$lib/stores/language';

    // =========================================================================
    // Props (Svelte 5)
    // =========================================================================

    interface Props {
        open?: boolean;
        /** Current date range for auto-sync after creation */
        dateStart?: string;
        dateEnd?: string;
        /** Edit mode: pre-populates currencies (read-only) for editing providers of existing pair */
        editMode?: boolean;
        /** Pre-populated base currency (used in editMode) */
        editBase?: string;
        /** Pre-populated quote currency (used in editMode) */
        editQuote?: string;
        /** Pre-populated routes (used in editMode) */
        editRoutes?: ChainStep[][];
        oncreated?: (detail: {base: string; quote: string; hasRealProvider: boolean}) => void;
        onclose?: () => void;
    }

    let {
        open = $bindable(false),
        dateStart = '',
        dateEnd = '',
        editMode = false,
        editBase = '',
        editQuote = '',
        editRoutes = [],
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
    /** When true, intermediate pairs from chain routes are auto-created on save */
    let createIntermediatePairs = $state(false);

    // Dirty/discard state
    let showDiscardConfirm = $state(false);

    // Baseline routes for edit mode dirty detection
    let baselineRoutesJson = $state('[]');

    // Populate state when editMode opens, and load routes from backend
    let loadingRoutes = $state(false);

    $effect(() => {
        if (open && editMode && editBase && editQuote) {
            baseCurrency = editBase;
            quoteCurrency = editQuote;
            // Load actual routes from backend for pre-existing pair
            loadRoutesFromBackend();
        }
    });

    async function loadRoutesFromBackend() {
        if (!editMode || !editBase || !editQuote) return;
        loadingRoutes = true;
        try {
            const response = await zodiosApi.list_routes_api_v1_fx_providers_routes_get();
            const items = (response as any)?.items || [];
            const pairRoutes = items
                .filter((i: any) =>
                    ((i.base === editBase && i.quote === editQuote) ||
                    (i.base === editQuote && i.quote === editBase)) &&
                    !(i.chain_steps?.length === 1 && i.chain_steps[0].provider === 'MANUAL')
                )
                .sort((a: any, b: any) => a.priority - b.priority);
            if (pairRoutes.length > 0) {
                selectedRoutes = pairRoutes.map((r: any) => r.chain_steps ?? []);
            } else if (editRoutes.length > 0) {
                selectedRoutes = [...editRoutes];
            } else {
                selectedRoutes = [];
            }
            // Snapshot baseline for dirty detection
            baselineRoutesJson = JSON.stringify(selectedRoutes);
        } catch (e) {
            console.error('Failed to load routes for edit mode:', e);
            // Fallback to prop
            selectedRoutes = editRoutes.length > 0 ? [...editRoutes] : [];
            baselineRoutesJson = JSON.stringify(selectedRoutes);
        } finally {
            loadingRoutes = false;
        }
    }

    // =========================================================================
    // Derived
    // =========================================================================

    let hasCurrencies = $derived(!!baseCurrency && !!quoteCurrency && baseCurrency !== quoteCurrency);
    let hasRoutes = $derived(selectedRoutes.length > 0);
    let hasChainRoutes = $derived(selectedRoutes.some(r => r.length > 1));
    let isValid = $derived(hasCurrencies);
    let isDirty = $derived.by(() => {
        if (editMode) {
            // In edit mode, dirty only if routes changed from baseline
            return JSON.stringify(selectedRoutes) !== baselineRoutesJson;
        }
        // In create mode, dirty if anything is set
        return baseCurrency !== '' || quoteCurrency !== '' || selectedRoutes.length > 0;
    });
    /** Slugs of already-configured FX pairs for sorting chain routes */
    let configuredPairSlugs = $derived(getRegisteredPairs());

    /**
     * Build a map: currency → Set of currencies it's already paired with.
     * Slugs are "BASE-QUOTE" alphabetically ordered, so both directions are covered.
     */
    let pairedWith = $derived.by(() => {
        const map = new Map<string, Set<string>>();
        for (const slug of configuredPairSlugs) {
            const [a, b] = slug.split('-');
            if (!map.has(a)) map.set(a, new Set());
            if (!map.has(b)) map.set(b, new Set());
            map.get(a)!.add(b);
            map.get(b)!.add(a);
        }
        return map;
    });

    /** Currencies the quote select must exclude: already paired with baseCurrency + baseCurrency itself */
    let excludedForQuote = $derived.by(() => {
        if (!baseCurrency) return new Set<string>();
        const excluded = new Set<string>([baseCurrency]);
        const partners = pairedWith.get(baseCurrency);
        if (partners) for (const p of partners) excluded.add(p);
        return excluded;
    });

    /** Currencies the base select must exclude: already paired with quoteCurrency + quoteCurrency itself */
    let excludedForBase = $derived.by(() => {
        if (!quoteCurrency) return new Set<string>();
        const excluded = new Set<string>([quoteCurrency]);
        const partners = pairedWith.get(quoteCurrency);
        if (partners) for (const p of partners) excluded.add(p);
        return excluded;
    });

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
            // Build the main pair routes
            const mainItems = selectedRoutes.length > 0
                ? selectedRoutes.map((chainSteps, idx) => ({
                    base, quote,
                    chain_steps: chainSteps,
                    priority: idx + 1,
                }))
                : [{
                    base, quote,
                    chain_steps: [{from: base, to: quote, provider: 'MANUAL'}],
                    priority: 999,
                }];

            // Collect intermediate pair routes if flag is on and there are chain routes
            const intermediateItems: typeof mainItems = [];
            if (createIntermediatePairs && selectedRoutes.some(r => r.length > 1)) {
                const existingSlugs = new Set(configuredPairSlugs);
                // Also include the main pair being created
                existingSlugs.add(`${base}-${quote}`);
                const added = new Set<string>(); // track to avoid duplicates across chains

                for (const chainSteps of selectedRoutes) {
                    for (const step of chainSteps) {
                        const iBase = step.from < step.to ? step.from : step.to;
                        const iQuote = step.from < step.to ? step.to : step.from;
                        const slug = `${iBase}-${iQuote}`;
                        if (existingSlugs.has(slug) || added.has(slug)) continue;
                        // Skip if it's the same as the main pair
                        if (iBase === base && iQuote === quote) continue;
                        added.add(slug);
                        intermediateItems.push({
                            base: iBase, quote: iQuote,
                            chain_steps: [{from: step.from, to: step.to, provider: step.provider}],
                            priority: 1,
                        });
                    }
                }
            }

            // Create all routes in one bulk call
            await zodiosApi.create_routes_bulk_api_v1_fx_providers_routes_post([
                ...mainItems,
                ...intermediateItems,
            ]);

            // Auto-sync if real routes exist (not MANUAL-only)
            const hasRealProvider = selectedRoutes.length > 0;
            if (hasRealProvider && dateStart && dateEnd) {
                syncing = true;
                try {
                    const mainSlug = base < quote ? `${base}-${quote}` : `${quote}-${base}`;
                    const pairsToSync = [mainSlug];
                    // Also sync newly created intermediate pairs
                    for (const item of intermediateItems) {
                        const iSlug = `${item.base}-${item.quote}`;
                        pairsToSync.push(iSlug);
                    }
                    await zodiosApi.sync_rates_api_v1_fx_currencies_sync_post({
                        pairs: pairsToSync,
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
        createIntermediatePairs = false;
        baselineRoutesJson = '[]';
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
                {editMode ? $_('fx.addPair.titleEdit') : $_('fx.addPair.title')}
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
            <!-- Currency selection — in editMode: disabled (readonly with flags) -->
            <!-- ========================================================= -->
            <div class="space-y-1.5">
                <div class="flex flex-col sm:flex-row items-stretch gap-2">
                    <div class="flex-1 min-w-0">
                        <div class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                            {$_('fx.addPair.baseCurrency')}
                        </div>
                        <CurrencySearchSelect
                            bind:value={baseCurrency}
                            placeholder={$_('fx.addPair.baseCurrency')}
                            excludedCurrencies={editMode ? new Set() : excludedForBase}
                            disabled={editMode}
                            onchange={() => {
                                if (!editMode) {
                                    // Auto-focus the quote currency select after picking base
                                    setTimeout(() => {
                                        const trigger = quoteSelectRef?.querySelector<HTMLElement>('[tabindex], input');
                                        trigger?.focus();
                                        if (!quoteCurrency) trigger?.click();
                                    }, 30);
                                }
                            }}
                        />
                    </div>
                    <!-- Arrow: ↔ on desktop, ↕ on mobile -->
                    <div class="text-gray-400 dark:text-gray-500 flex-shrink-0 hidden sm:flex flex-col items-center">
                        <div class="text-xs font-medium invisible mb-1 select-none" aria-hidden="true">&nbsp;</div>
                        <div class="flex-1 flex items-center justify-center px-1">
                            <ArrowLeftRight size={18} />
                        </div>
                    </div>
                    <div class="text-gray-400 dark:text-gray-500 flex-shrink-0 flex items-center justify-center sm:hidden">
                        <ArrowDownUp size={18} />
                    </div>
                    <div class="flex-1 min-w-0" bind:this={quoteSelectRef}>
                        <div class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                            {$_('fx.addPair.quoteCurrency')}
                        </div>
                        <CurrencySearchSelect
                            bind:value={quoteCurrency}
                            placeholder={$_('fx.addPair.quoteCurrency')}
                            excludedCurrencies={editMode ? new Set() : excludedForQuote}
                            disabled={editMode}
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
                    language={$currentLanguage}
                    disabled={!hasCurrencies}
                    {configuredPairSlugs}
                />

                <!-- Create intermediate pairs checkbox (visible only when chain routes are selected) -->
                {#if hasChainRoutes}
                    <label class="flex items-start gap-2 p-2.5 bg-blue-50 dark:bg-blue-900/10 rounded-lg border border-blue-200 dark:border-blue-800 cursor-pointer hover:bg-blue-100/50 dark:hover:bg-blue-900/20 transition-colors">
                        <input
                            type="checkbox"
                            bind:checked={createIntermediatePairs}
                            class="mt-0.5 rounded border-gray-300 dark:border-slate-600 text-libre-green focus:ring-libre-green"
                        />
                        <div class="text-xs text-blue-700 dark:text-blue-300 leading-relaxed">
                            <span class="font-medium">{$_('fx.addPair.createIntermediatePairs')}</span>
                            <p class="text-blue-500 dark:text-blue-400 mt-0.5">{$_('fx.addPair.createIntermediatePairsHint')}</p>
                        </div>
                    </label>
                {/if}
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
                    {$_('fx.syncing')}
                {:else if saving}
                    {$_('common.saving')}
                {:else}
                    {$_('common.saveConfiguration')}
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
