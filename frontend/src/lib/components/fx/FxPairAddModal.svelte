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
    import {onDestroy} from 'svelte';
    import {get} from 'svelte/store';
    import {zodiosApi} from '$lib/api';
    import {trySave} from '$lib/utils/trySave';
    import {ArrowDownUp, ArrowLeftRight, Lock, X} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import {getClientSessionGeneration, isClientSessionCurrent} from '$lib/stores/app/clientSession';
    import {notify} from '$lib/stores/app/notify.svelte';
    import {finishFxPairCreation, type FxPairCreatedDetail, type FxPairSyncCompleteDetail} from '$lib/services/fxCreationSync';
    import {fxPairHtml} from '$lib/utils/providerHelpers';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import {ConfirmModal} from '$lib/components/table';
    import {CurrencySearchSelect, FxProviderSelect} from '$lib/components/ui/select';
    import type {ChainStep} from '$lib/utils/currency/currencyGraph';
    import {getRegisteredPairs} from '$lib/stores/fxStoreRegistry';
    import {ensureFxRoutesLoaded, getConfiguredPairSlugs, fxRoutesVersion} from '$lib/stores/reference/fxRoutesStore';
    import {currentLanguage} from '$lib/stores/app/language';

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
        /** Initial base currency for create mode (editable, not locked) */
        initialBase?: string;
        /** Initial quote currency for create mode (editable, not locked) */
        initialQuote?: string;
        /** Lock the base currency field (e.g. when creating FX from asset detail) */
        readonlyBase?: boolean;
        /** Configuration committed; does not wait for automatic rate sync. */
        oncreated?: (detail: FxPairCreatedDetail) => void | Promise<void>;
        /** Automatic sync settled, including partial, failed and skipped outcomes. */
        onsynced?: (detail: FxPairSyncCompleteDetail) => void | Promise<void>;
        onclose?: () => void;
    }

    let {open = $bindable(false), dateStart = '', dateEnd = '', editMode = false, editBase = '', editQuote = '', editRoutes = [], initialBase = '', initialQuote = '', readonlyBase = false, oncreated, onsynced, onclose}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let baseCurrency = $state('');
    let quoteCurrency = $state('');
    let selectedRoutes = $state<ChainStep[][]>([]);
    let saving = $state(false);
    let saveAdmission = 0;
    onDestroy(() => {
        saveAdmission += 1;
    });
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

    // Pre-fill currencies in create mode (editable, not locked)
    $effect(() => {
        if (open && !editMode) {
            if (initialBase && !baseCurrency) baseCurrency = initialBase;
            if (initialQuote && !quoteCurrency) quoteCurrency = initialQuote;
        }
    });

    // Load backend-configured routes when the modal opens so pair exclusion
    // reflects the real backend state, not just the lazily-populated session cache.
    $effect(() => {
        if (open) void ensureFxRoutesLoaded();
    });

    async function loadRoutesFromBackend() {
        if (!editMode || !editBase || !editQuote) return;
        loadingRoutes = true;
        try {
            const response = await zodiosApi.list_routes_api_v1_fx_providers_routes_get();
            const items = response?.items ?? [];
            const pairRoutes = items.filter((i) => ((i.base === editBase && i.quote === editQuote) || (i.base === editQuote && i.quote === editBase)) && !(!i.is_chain && i.chain_steps[0]?.provider === 'MANUAL')).sort((a, b) => a.priority - b.priority);
            if (pairRoutes.length > 0) {
                selectedRoutes = pairRoutes.map((r) => r.chain_steps ?? []);
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
    let hasChainRoutes = $derived(selectedRoutes.some((r) => r.length > 1));
    let isValid = $derived(hasCurrencies);
    let isDirty = $derived.by(() => {
        if (editMode) {
            // In edit mode, dirty only if routes changed from baseline
            return JSON.stringify(selectedRoutes) !== baselineRoutesJson;
        }
        // In create mode, dirty if anything is set
        return baseCurrency !== '' || quoteCurrency !== '' || selectedRoutes.length > 0;
    });
    /** Slugs of already-configured FX pairs for sorting chain routes.
     *  Merge backend routes (authoritative, via fxRoutesStore) with the session
     *  registry so exclusion works even before the registry cache is populated. */
    let configuredPairSlugs = $derived.by(() => {
        void $fxRoutesVersion; // re-run when routes reload/invalidate
        return [...new Set<string>([...getConfiguredPairSlugs(), ...getRegisteredPairs()])];
    });

    let pairAlreadyExists = $derived.by(() => {
        void $fxRoutesVersion;
        if (editMode || !baseCurrency || !quoteCurrency || baseCurrency === quoteCurrency) return false;
        const base = baseCurrency.toUpperCase();
        const quote = quoteCurrency.toUpperCase();
        const slug = base < quote ? `${base}-${quote}` : `${quote}-${base}`;
        return getConfiguredPairSlugs().has(slug);
    });

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

    /** Currencies the quote select must exclude: already paired with baseCurrency + baseCurrency itself.
     *  The currently-selected quoteCurrency is never excluded, so a pre-filled/already-configured
     *  pair (e.g. EUR/USD opened from a "missing pair" banner) stays visible and selectable. */
    let excludedForQuote = $derived.by(() => {
        if (!baseCurrency) return new Set<string>();
        const excluded = new Set<string>([baseCurrency]);
        const partners = pairedWith.get(baseCurrency);
        if (partners) for (const p of partners) excluded.add(p);
        if (quoteCurrency) excluded.delete(quoteCurrency);
        return excluded;
    });

    /** Currencies the base select must exclude: already paired with quoteCurrency + quoteCurrency itself.
     *  The currently-selected baseCurrency is never excluded (see excludedForQuote note). */
    let excludedForBase = $derived.by(() => {
        if (!quoteCurrency) return new Set<string>();
        const excluded = new Set<string>([quoteCurrency]);
        const partners = pairedWith.get(quoteCurrency);
        if (partners) for (const p of partners) excluded.add(p);
        if (baseCurrency) excluded.delete(baseCurrency);
        return excluded;
    });

    // =========================================================================
    // Handlers
    // =========================================================================

    function handleRoutesChange(routes: ChainStep[][]) {
        selectedRoutes = routes;
    }

    async function handleSave() {
        if (!isValid || saving) return;

        const base = baseCurrency.toUpperCase() < quoteCurrency.toUpperCase() ? baseCurrency.toUpperCase() : quoteCurrency.toUpperCase();
        const quote = baseCurrency.toUpperCase() < quoteCurrency.toUpperCase() ? quoteCurrency.toUpperCase() : baseCurrency.toUpperCase();
        const slug = `${base}-${quote}`;
        const routes = selectedRoutes.map((route) => route.map(({from, to, provider}) => ({from, to, provider})));
        const includeIntermediates = createIntermediatePairs;
        const editing = editMode;
        const start = dateStart;
        const end = dateEnd;
        const createdCallback = oncreated;
        const syncedCallback = onsynced;
        const closeCallback = onclose;
        const configuredSlugsAtSave = new Set(configuredPairSlugs);
        const sessionGeneration = getClientSessionGeneration();
        const admission = ++saveAdmission;
        const sameSession = () => isClientSessionCurrent(sessionGeneration);
        const current = () => admission === saveAdmission && sameSession();
        const reportConfigurationError = (message: string) => {
            if (!sameSession()) return;
            if (current()) {
                error = message;
            } else {
                notify({
                    name: 'fx.pair.configuration-failed',
                    detail: {slug, editMode: editing, sessionGeneration},
                    toast: {variant: 'error', message: `${fxPairHtml(slug, {outerFlags: true})}\n${escapeHtml(message)}`},
                });
            }
        };
        saving = true;
        error = null;

        try {
            if (!editing) {
                await ensureFxRoutesLoaded();
                if (!sameSession() || getConfiguredPairSlugs().has(slug)) return;
            }
            // Build the main pair routes
            const mainItems =
                routes.length > 0
                    ? routes.map((chainSteps, idx) => ({
                          base,
                          quote,
                          chain_steps: chainSteps.map(({from, to, provider}) => ({from, to, provider})),
                          priority: idx + 1,
                      }))
                    : [
                          {
                              base,
                              quote,
                              chain_steps: [{from: base, to: quote, provider: 'MANUAL'}],
                              priority: 999,
                          },
                      ];

            // Collect intermediate pair routes if flag is on and there are chain routes
            const intermediateItems: typeof mainItems = [];
            if (includeIntermediates && routes.some((r) => r.length > 1)) {
                const existingSlugs = new Set([...configuredSlugsAtSave, ...getConfiguredPairSlugs()]);
                // Also include the main pair being created
                existingSlugs.add(`${base}-${quote}`);
                const added = new Set<string>(); // track to avoid duplicates across chains

                for (const chainSteps of routes) {
                    for (const step of chainSteps) {
                        const iBase = step.from < step.to ? step.from : step.to;
                        const iQuote = step.from < step.to ? step.to : step.from;
                        const slug = `${iBase}-${iQuote}`;
                        if (existingSlugs.has(slug) || added.has(slug)) continue;
                        // Skip if it's the same as the main pair
                        if (iBase === base && iQuote === quote) continue;
                        added.add(slug);
                        intermediateItems.push({
                            base: iBase,
                            quote: iQuote,
                            chain_steps: [{from: step.from, to: step.to, provider: step.provider}],
                            priority: 1,
                        });
                    }
                }
            }

            const hasRealProvider = routes.some((route) => route.some((step) => step.provider !== 'MANUAL'));
            const context = {
                detail: {base, quote, slug, hasRealProvider, autoSyncStarted: !editing && hasRealProvider && !!start && !!end},
                pairs: [slug, ...intermediateItems.map((item) => `${item.base}-${item.quote}`)],
                start,
                end,
                sessionGeneration,
                editMode: editing,
                oncreated: (createdDetail: FxPairCreatedDetail) => {
                    if (current()) return createdCallback?.(createdDetail);
                },
                onsynced: syncedCallback,
                onclose: () => {
                    if (current()) resetAndClose(() => closeCallback?.());
                },
            };

            // In edit mode, delete all existing routes for this pair first
            // to ensure stale routes don't persist (e.g., when user removes all providers).
            // The backend auto-reinstates a MANUAL sentinel if no routes remain after delete.
            if (editing) {
                const deleteResult = await trySave(() => zodiosApi.delete_routes_bulk_api_v1_fx_providers_routes_delete([{base, quote}]), {toast: false, fallback: get(_)('fx.addPair.createFailed')});
                if (!sameSession()) return;
                if (deleteResult.status === 'error') {
                    reportConfigurationError(deleteResult.message);
                    return;
                }
                // If user removed all providers, backend already reinstated MANUAL — skip POST
                if (routes.length === 0) {
                    void finishFxPairCreation(context);
                    return;
                }
            }

            const createResult = await trySave(() => zodiosApi.create_routes_bulk_api_v1_fx_providers_routes_post([...mainItems, ...intermediateItems]), {toast: false, fallback: get(_)('fx.addPair.createFailed')});
            if (!sameSession()) return;
            if (createResult.status === 'error') {
                // A 409 is the concurrent-write conflict, and it is the one case
                // where the backend's own sentence must not reach the screen:
                // `extractErrorMessage` returns `detail` verbatim, and for a long
                // time that meant the user read a driver traceback with the INSERT
                // statement and its bound parameters in it. The conflict is also
                // the only failure here the user can do something about, so it is
                // the one that deserves a translated sentence telling them to.
                reportConfigurationError(createResult.status_code === 409 ? get(_)('fx.addPair.createConflict') : createResult.message);
                return;
            }

            void finishFxPairCreation(context);
        } finally {
            if (current()) saving = false;
        }
    }

    /** Try to close — show confirm if dirty */
    function handleClose() {
        if (saving) return;
        if (isDirty) {
            showDiscardConfirm = true;
        } else {
            resetAndClose();
        }
    }

    /** Actually reset and close */
    function resetAndClose(closeCallback = onclose) {
        saveAdmission += 1;
        saving = false;
        baseCurrency = '';
        quoteCurrency = '';
        selectedRoutes = [];
        createIntermediatePairs = false;
        baselineRoutesJson = '[]';
        error = null;
        showDiscardConfirm = false;
        // Close the modal directly (open is $bindable). Callers that bind:open rely on this;
        // onclose remains for callers that need a side-effect hook.
        open = false;
        closeCallback?.();
    }
</script>

<ModalBase allowOverflow={true} maxWidth="lg" onRequestClose={handleClose} {open}>
    <div class="flex flex-col max-h-[90vh] min-h-[50vh]" data-testid="fx-add-pair-modal">
        <!-- ============================================================= -->
        <!-- Header -->
        <!-- ============================================================= -->
        <div class="flex items-center justify-between p-5 pb-4 border-b border-gray-100 dark:border-slate-700 shrink-0">
            <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100">
                {editMode ? $_('fx.addPair.titleEdit') : $_('fx.addPair.title')}
            </h2>
            <button class="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors disabled:opacity-50" disabled={saving} onclick={handleClose}>
                <X size={20} />
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
                    <div class="flex-1 min-w-0" data-testid="fx-add-pair-base">
                        <div class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                            {$_('fx.addPair.baseCurrency')}
                        </div>
                        <CurrencySearchSelect
                            bind:value={baseCurrency}
                            disabled={saving || editMode || readonlyBase}
                            excludedCurrencies={editMode || readonlyBase ? new Set() : excludedForBase}
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
                            placeholder={$_('fx.addPair.baseCurrency')}
                        />
                    </div>
                    <!-- Arrow: ↔ on desktop, ↕ on mobile -->
                    <div class="text-gray-400 dark:text-gray-500 flex-shrink-0 hidden sm:flex flex-col items-center">
                        <div aria-hidden="true" class="text-xs font-medium invisible mb-1 select-none">&nbsp;</div>
                        <div class="flex-1 flex items-center justify-center px-1">
                            <ArrowLeftRight size={18} />
                        </div>
                    </div>
                    <div class="text-gray-400 dark:text-gray-500 flex-shrink-0 flex items-center justify-center sm:hidden">
                        <ArrowDownUp size={18} />
                    </div>
                    <div bind:this={quoteSelectRef} class="flex-1 min-w-0" data-testid="fx-add-pair-quote">
                        <div class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                            {$_('fx.addPair.quoteCurrency')}
                        </div>
                        <CurrencySearchSelect bind:value={quoteCurrency} disabled={saving || editMode} excludedCurrencies={editMode ? new Set() : excludedForQuote} placeholder={$_('fx.addPair.quoteCurrency')} />
                    </div>
                </div>
            </div>

            {#if pairAlreadyExists}
                <InfoBanner variant="warning">
                    {$_('fx.addPair.alreadyExists')}
                </InfoBanner>
            {/if}

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
                <FxProviderSelect {baseCurrency} bind:selectedRoutes {configuredPairSlugs} disabled={saving || !hasCurrencies} language={$currentLanguage} onSelectionChange={handleRoutesChange} {quoteCurrency} />

                <!-- Create intermediate pairs checkbox (visible only when chain routes are selected) -->
                {#if hasChainRoutes}
                    <label class="flex items-start gap-2 p-2.5 bg-blue-50 dark:bg-blue-900/10 rounded-lg border border-blue-200 dark:border-blue-800 cursor-pointer hover:bg-blue-100/50 dark:hover:bg-blue-900/20 transition-colors">
                        <input type="checkbox" bind:checked={createIntermediatePairs} disabled={saving} data-testid="fx-add-pair-intermediates" class="mt-0.5 rounded border-gray-300 dark:border-slate-600 text-libre-green focus:ring-libre-green" />
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
            <button class="px-3 py-1.5 text-sm bg-gray-200 dark:bg-slate-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-slate-500 transition-colors" disabled={saving} onclick={handleClose} type="button">
                {$_('common.cancel')}
            </button>
            <button
                class="px-3 py-1.5 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
                data-testid="fx-add-pair-save"
                disabled={!isValid || pairAlreadyExists || saving}
                onclick={handleSave}
                type="button"
            >
                {#if saving}
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
    confirmText={$_('common.discard')}
    danger={false}
    message={$_('common.discardChangesMessage')}
    onCancel={() => {
        showDiscardConfirm = false;
    }}
    onConfirm={resetAndClose}
    open={showDiscardConfirm}
    title={$_('common.discardChanges')}
    warning={true}
    zIndex={70}
/>
