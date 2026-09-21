<script lang="ts">
    /**
     * AssetSetRiskPanel — the laboratory.
     *
     * This panel used to open on `assets.slice(0, 100)`: a hundred instruments,
     * a ten-thousand-cell matrix with its numbers already suppressed, and no
     * way back except ninety-odd clicks on an X. The system made a bad choice
     * on the user's behalf and then hid the undo.
     *
     * What changed:
     *
     * - the opening set is **remembered**, then **owned**, then **small** — see
     *   `resolveInitialSelection`; the hundred survives only as the API's
     *   ceiling;
     * - four mass actions and two filters make a large set reachable *and*
     *   escapable;
     * - the broker control stopped pretending to be a filter. It was never one:
     *   it replaced the selection wholesale. It is now labelled as what it
     *   does — a preset that loads a broker's assets — and choosing its empty
     *   option no longer wipes the selection.
     *
     * **No amount of money appears anywhere on this page.** Not in this panel,
     * not in the levels mounted below it. An asset set has no weights, so any
     * euro figure would be an arithmetic claim about a portfolio the user never
     * described. Percentages and coefficients only.
     *
     * WHY THE LEGACY PANEL IS NO LONGER MOUNTED HERE, and why removing it took
     * nothing away. `RiskAnalysisPanel` gates each of its eight sections on a
     * capability the backend advertises for the scope (`:124-130`), and on
     * `asset_set` the backend advertises **two** analytics: `correlation` and
     * `stress`. So on this page the legacy contributed exactly two things, and
     * both were defects:
     *
     *   - a **second** correlation matrix, identical to the one above it, which
     *     put two `risk-correlation-heatmap` nodes in one document and made
     *     every selector inside it ambiguous under Playwright strict mode;
     *   - the **hypothetical shock**, which `03-mappa-livelli-pagine` §3.3
     *     forbids here: without weights it rewrites its own input in a different
     *     shape and calls the result a scenario.
     *
     * Its historical replay — the one rung this page *is* allowed to show — was
     * unreachable from here anyway: `:874` is `{#if scope.kind === 'asset'}`,
     * nested inside `{#if supportsStress}`. The page showed the forbidden rung
     * and hid the permitted one, which is what `AssetSetReplaySection` now
     * corrects.
     *
     * 🔴 The component itself is **not** deleted: `AssetRiskScenariosView:89`
     * still mounts it for Asset Detail, which `03` parks in beta and keeps out
     * of this redesign. What left is one mount, not the code.
     */
    import {untrack} from 'svelte';
    import {CheckCheck, FlipHorizontal, RefreshCw, Square, Undo2, X} from 'lucide-svelte';

    import {_ as t} from '$lib/i18n';
    import AssetSelect from '$lib/components/ui/select/AssetSelect.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import {singleValue} from '$lib/risk/riskTypes';
    import {fetchReport} from '$lib/stores/portfolio/portfolioStore.svelte';
    import {assetStoreVersion, getAssetInfo} from '$lib/stores/reference/assetStore';
    import {brokerStoreVersion, ensureBrokersLoaded, getAccessibleBrokers} from '$lib/stores/reference/brokerStore';
    import AssetSetCorrelationSection from './AssetSetCorrelationSection.svelte';
    import AssetSetComparisonLevels from './AssetSetComparisonLevels.svelte';
    import AssetSetReplaySection from './AssetSetReplaySection.svelte';
    import RiskBetaBanner from './RiskBetaBanner.svelte';
    import {riskBenchmark} from '$lib/stores/risk/riskBenchmarkStore.svelte';
    import {applyBulkAction, applyFilters, MAX_SELECTED_ASSETS, readPersistedSelection, resolveInitialSelectionWithSource, writePersistedSelection, type BulkAction, type SelectionFilters, type SelectionSource} from './assetSetSelection';

    interface AssetOption {
        id: number;
        display_name: string;
        currency: string;
        icon_url?: string | null;
        asset_type?: string | null;
        provider_code?: string | null;
        active?: boolean;
        /** Transactions in brokers the user owns — what "my assets" means here. */
        tx_count_own?: number;
    }

    interface Props {
        assets: AssetOption[];
        dateStart: string;
        dateEnd: string;
        targetCurrency: string;
    }

    let {assets, dateStart, dateEnd, targetCurrency}: Props = $props();

    let selectedAssetIds = $state<number[]>([]);
    let brokerPreset = $state('');
    let filters = $state<SelectionFilters>({types: [], currencies: []});
    let brokerAssetsLoading = $state(false);
    let brokerLoadFailed = $state(false);
    let seedInitialized = false;
    let selectionSource = $state<SelectionSource | null>(null);
    let brokerRequestGeneration = 0;
    let lastBrokerSignature = '';

    let brokers = $derived.by(() => {
        void $brokerStoreVersion;
        return getAccessibleBrokers();
    });
    let brokerOptions = $derived([{value: '', label: $t('risk.assetSet.presetNone')}, ...brokers.map((broker) => ({value: String(broker.id), label: broker.name}))]);
    let selectedAssets = $derived(selectedAssetIds.map((assetId) => assets.find((asset) => asset.id === assetId)).filter((asset): asset is AssetOption => Boolean(asset)));

    /**
     * Filter options come from the **whole** catalogue, never from the filtered
     * result. Deriving them from what survives the filter is how a selected
     * option disappears the moment it is applied, leaving a filter the user
     * cannot switch off (`problems/datatable-filter-options-disappear`).
     */
    let typeOptions = $derived([...new Set(assets.map((asset) => asset.asset_type || 'OTHER'))].sort());
    let currencyOptions = $derived([...new Set(assets.map((asset) => asset.currency))].sort());
    let candidates = $derived(applyFilters(assets, filters));
    let filtersActive = $derived(filters.types.length > 0 || filters.currencies.length > 0);
    let atCapacity = $derived(selectedAssetIds.length >= MAX_SELECTED_ASSETS);

    /**
     * `AssetSelect` is backed by the global asset cache, while this panel is
     * driven by the page's own list. Restricting the picker to ids the page
     * knows keeps the two in step: an asset chosen from the wider cache would
     * enter `selectedAssetIds`, reach the API, and then fail to resolve into a
     * chip here — present in the analysis, invisible in the controls.
     */
    let pageAssetIds = $derived(new Set(assets.map((asset) => asset.id)));

    /**
     * Names for the matrix's axes.
     *
     * Built from the page's own list first, because this panel already holds
     * every display name it put in the selection: no store round-trip, no
     * version token, and no `#id` for anything the reader picked themselves.
     * The store is consulted only for the case the comment above describes —
     * an id remembered from a previous visit that is no longer on the page,
     * present in the analysis and invisible in the controls. Dropping that
     * lookup would have been a quiet regression: the legacy resolved those ids
     * through the store, so they show a name today.
     */
    let selectionLabels = $derived.by(() => {
        void $assetStoreVersion;
        const labels = new Map<number, string>();
        for (const asset of selectedAssets) labels.set(asset.id, asset.display_name);
        for (const assetId of selectedAssetIds) {
            if (labels.has(assetId)) continue;
            const name = getAssetInfo(assetId)?.display_name;
            if (name) labels.set(assetId, name);
        }
        return labels;
    });

    $effect(() => {
        untrack(() => void ensureBrokersLoaded());
    });

    $effect(() => {
        if (seedInitialized || assets.length === 0) return;
        seedInitialized = true;
        const seed = resolveInitialSelectionWithSource(assets, readPersistedSelection());
        selectedAssetIds = seed.ids;
        selectionSource = seed.source;
    });

    /** Remember the set, so the next visit starts where this one ended. */
    $effect(() => {
        const ids = selectedAssetIds;
        if (!seedInitialized) return;
        untrack(() => writePersistedSelection(ids));
    });

    $effect(() => {
        const signature = `${brokerPreset}|${dateStart}|${dateEnd}|${targetCurrency}`;
        if (signature === lastBrokerSignature) return;
        lastBrokerSignature = signature;
        untrack(() => void applyBrokerPreset());
    });

    /**
     * Load a broker's holdings into the selection.
     *
     * The empty option is the control's *null state*, not an instruction: it
     * used to reset the selection to the first hundred assets, which meant the
     * only way to clear a broker preset was to trigger the very behaviour this
     * panel was rewritten to remove.
     *
     * `fetchReport` is a portfolio route, but only the holdings' `asset_id`s are
     * read from it — no amount, no weight, no valuation crosses into this page.
     */
    async function applyBrokerPreset(): Promise<void> {
        const generation = ++brokerRequestGeneration;
        brokerLoadFailed = false;
        if (!brokerPreset) return;

        brokerAssetsLoading = true;
        try {
            const report = await fetchReport([Number(brokerPreset)], dateStart, dateEnd, targetCurrency);
            if (generation !== brokerRequestGeneration) return;
            const summary = singleValue(report?.summary);
            selectedAssetIds = [...new Set((summary?.holdings ?? []).map((holding) => holding.asset_id))].sort((left, right) => left - right).slice(0, MAX_SELECTED_ASSETS);
        } catch (error) {
            console.error('[Risk] Failed to resolve broker asset set:', error);
            if (generation === brokerRequestGeneration) brokerLoadFailed = true;
        } finally {
            if (generation === brokerRequestGeneration) brokerAssetsLoading = false;
        }
    }

    /**
     * The benchmark the comparison levels measure against, when one applies.
     *
     * Read from the shared `riskBenchmark` and never from a picker of this page's
     * own: `03-mappa-livelli-pagine` §3.1 makes the benchmark identical across
     * scopes, because two pages comparing against different references stop being
     * comparable — which is the property the redesign exists to build.
     *
     * 🔴 **Mirrored through `$effect` and not read inside a `$derived`, and that
     * is a correctness requirement rather than a style.** `riskBenchmark.assetId`
     * is a getter that *hydrates on read*: it calls `localStorage` and assigns to
     * the store's `$state`. Writing state while a derived is being evaluated is
     * fatal in runes mode, so reading it from a `$derived` threw and took the
     * whole `{#if}` block with it — the controls stayed on screen and every
     * section below them vanished, which looks exactly like "no assets selected".
     * An effect may write, so the choice is mirrored here and derived from the
     * mirror. `L3Benchmark` gets away with a direct read because its read happens
     * inside a handler, not inside a derivation.
     */
    let benchmarkChoice = $state<number | null>(null);

    $effect(() => {
        // Reading inside the effect both triggers the hydration and subscribes to
        // the store's state, so a benchmark chosen on another page still arrives.
        benchmarkChoice = riskBenchmark.assetId;
    });

    /**
     * 🔴 Withheld when the benchmark is itself one of the selected assets.
     * `RiskAssetSetComparisonOutput` rejects that outright — "the comparison
     * asset cannot appear among the compared items" — because a yardstick cannot
     * also be one of the measured. Asking anyway would turn a coherent state into
     * a validation error the reader has no way to act on, so the request simply
     * does not carry it and L3° says the columns are unavailable.
     */
    let benchmarkId = $derived(benchmarkChoice !== null && !selectedAssetIds.includes(benchmarkChoice) ? benchmarkChoice : null);

    function runBulkAction(action: BulkAction): void {
        selectedAssetIds = applyBulkAction(action, selectedAssetIds, candidates, assets).sort((left, right) => left - right);
    }

    function toggleFilter(kind: 'types' | 'currencies', value: string): void {
        const current = filters[kind];
        const next = current.includes(value) ? current.filter((entry) => entry !== value) : [...current, value];
        filters = {...filters, [kind]: next};
    }

    function clearFilters(): void {
        filters = {types: [], currencies: []};
    }

    function addAsset(assetId: number | null): void {
        if (assetId === null || selectedAssetIds.includes(assetId) || atCapacity) return;
        selectedAssetIds = [...selectedAssetIds, assetId].sort((left, right) => left - right);
    }

    function removeAsset(assetId: number): void {
        selectedAssetIds = selectedAssetIds.filter((id) => id !== assetId);
    }

    const BULK_ACTIONS: {action: BulkAction; icon: typeof CheckCheck; key: string}[] = [
        {action: 'all', icon: CheckCheck, key: 'selectAll'},
        {action: 'none', icon: Square, key: 'selectNone'},
        {action: 'invert', icon: FlipHorizontal, key: 'invert'},
        {action: 'mine', icon: Undo2, key: 'mine'},
    ];
</script>

<div class="space-y-4" data-testid="asset-global-risk-panel">
    <RiskBetaBanner />

    <section class="rounded-xl border border-gray-100 dark:border-slate-700 bg-white dark:bg-slate-800 p-4" data-testid="risk-asset-set-controls" data-selection-source={selectionSource}>
        <div class="flex flex-wrap items-end gap-3">
            <label class="text-xs text-gray-500 dark:text-gray-400">
                {$t('risk.assetSet.presetBroker')}
                <div class="mt-1 w-56">
                    <SimpleSelect value={brokerPreset} options={brokerOptions} compact testId="risk-broker-filter" optionTestId={(option) => `risk-broker-option-${option.value || 'all'}`} onchange={(value) => (brokerPreset = value)} />
                </div>
            </label>
            <label class="text-xs text-gray-500 dark:text-gray-400">
                {$t('risk.assetSet.addAsset')}
                <div class="mt-1 w-72 max-w-full">
                    <AssetSelect value={null} compact testid="risk-asset-add-select" disabled={atCapacity} filter={(asset) => pageAssetIds.has(asset.id) && !selectedAssetIds.includes(asset.id)} placeholder={$t('risk.assetSet.addAsset')} onchange={addAsset} />
                </div>
            </label>
            {#if brokerAssetsLoading}
                <RefreshCw size={16} class="animate-spin text-libre-green" data-testid="risk-broker-filter-loading" />
            {/if}
        </div>

        {#if brokerLoadFailed}
            <p class="mt-2 text-xs text-red-600 dark:text-red-400" data-testid="risk-broker-filter-error">{$t('risk.states.loadFailed')}</p>
        {/if}

        <div class="mt-4 flex flex-wrap items-center gap-2" data-testid="risk-asset-set-bulk-actions">
            {#each BULK_ACTIONS as { action, icon: Icon, key } (action)}
                <button
                    type="button"
                    class="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-40 dark:border-slate-600 dark:text-gray-300 dark:hover:bg-slate-700"
                    onclick={() => runBulkAction(action)}
                    disabled={assets.length === 0 || (action === 'all' && atCapacity)}
                    data-testid="risk-bulk-{action}"
                >
                    <Icon size={13} />
                    {$t(`risk.assetSet.bulk.${key}`)}
                </button>
            {/each}
            <span class="ml-auto text-xs text-gray-500 dark:text-gray-400" data-testid="risk-selected-count" data-selected={selectedAssetIds.length} data-total={candidates.length}>
                {$t('risk.assetSet.selectedCount', {values: {selected: selectedAssetIds.length, total: candidates.length}})}
            </span>
        </div>

        <div class="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2" data-testid="risk-asset-set-filters">
            <div class="flex flex-wrap items-center gap-1.5">
                <span class="text-xs text-gray-500 dark:text-gray-400">{$t('risk.assetSet.filters.type')}</span>
                {#each typeOptions as type (type)}
                    <button
                        type="button"
                        class="rounded-full border px-2 py-0.5 text-[11px] font-medium transition-colors {filters.types.includes(type)
                            ? 'border-libre-green bg-libre-green/10 text-libre-green'
                            : 'border-gray-200 text-gray-500 hover:bg-gray-50 dark:border-slate-600 dark:text-gray-400 dark:hover:bg-slate-700'}"
                        aria-pressed={filters.types.includes(type)}
                        onclick={() => toggleFilter('types', type)}
                        data-testid="risk-filter-type-{type}"
                    >
                        {$t(`assets.types.${type}`) || type}
                    </button>
                {/each}
            </div>
            <div class="flex flex-wrap items-center gap-1.5">
                <span class="text-xs text-gray-500 dark:text-gray-400">{$t('risk.assetSet.filters.currency')}</span>
                {#each currencyOptions as currency (currency)}
                    <button
                        type="button"
                        class="rounded-full border px-2 py-0.5 text-[11px] font-medium transition-colors {filters.currencies.includes(currency)
                            ? 'border-libre-green bg-libre-green/10 text-libre-green'
                            : 'border-gray-200 text-gray-500 hover:bg-gray-50 dark:border-slate-600 dark:text-gray-400 dark:hover:bg-slate-700'}"
                        aria-pressed={filters.currencies.includes(currency)}
                        onclick={() => toggleFilter('currencies', currency)}
                        data-testid="risk-filter-currency-{currency}"
                    >
                        {currency}
                    </button>
                {/each}
            </div>
            {#if filtersActive}
                <button type="button" class="text-xs text-libre-green hover:underline" onclick={clearFilters} data-testid="risk-filters-clear">{$t('risk.assetSet.filters.clear')}</button>
            {/if}
        </div>

        <div class="mt-3 flex flex-wrap gap-2" data-testid="risk-selected-assets">
            {#each selectedAssets as asset (asset.id)}
                <span class="inline-flex items-center gap-1 rounded-full bg-gray-100 dark:bg-slate-700 px-2 py-1 text-xs text-gray-600 dark:text-gray-300" data-testid="risk-selected-asset-{asset.id}">
                    {asset.display_name}
                    <button class="rounded-full p-0.5 hover:bg-gray-200 dark:hover:bg-slate-600" onclick={() => removeAsset(asset.id)} title={$t('common.remove')} data-testid="risk-remove-asset-{asset.id}">
                        <X size={11} />
                    </button>
                </span>
            {/each}
        </div>
        {#if atCapacity}
            <p class="mt-2 text-xs text-amber-600 dark:text-amber-400">{$t('risk.assetSet.maxAssets')}</p>
        {/if}
    </section>

    {#if selectedAssetIds.length > 0}
        <AssetSetCorrelationSection assetIds={selectedAssetIds} assetLabels={selectionLabels} {dateStart} {dateEnd} {targetCurrency} />
        <AssetSetComparisonLevels assetIds={selectedAssetIds} assetLabels={selectionLabels} {dateStart} {dateEnd} {targetCurrency} {benchmarkId} />
        <AssetSetReplaySection assetIds={selectedAssetIds} assetLabels={selectionLabels} {dateStart} {dateEnd} {targetCurrency} />
    {:else}
        <div class="rounded-xl border border-gray-100 dark:border-slate-700 bg-white dark:bg-slate-800 p-8 text-center text-sm text-gray-400 dark:text-gray-500" data-testid="risk-asset-set-empty">
            {$t('risk.states.noAssets')}
        </div>
    {/if}
</div>
