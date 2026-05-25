<script lang="ts">
    /**
     * WacPreviewSection — WAC preview with Auto/Manual toggle for cost_basis_override.
     *
     * Used in: TransactionFormModal (TRANSFER + ADJUSTMENT), BulkModal cells, PromoteMergeModal.
     *
     * Modes:
     * - "auto-new": toggle visible, Auto ON by default, live recalculation
     * - "saved": no toggle, shows saved value black, [↺ Recalculate] on-demand
     */
    import {t} from 'svelte-i18n';
    import {RefreshCw, ChevronDown, ChevronRight, Lightbulb, AlertTriangle} from 'lucide-svelte';
    import CompactCashCell from '$lib/components/ui/CompactCashCell.svelte';
    import Tooltip from '$lib/components/ui/Tooltip.svelte';
    import DocsLink from '$lib/components/ui/DocsLink.svelte';
    import {zodiosApi} from '$lib/api';
    import {getTransactionTypeIconUrl} from '$lib/stores/transactionTypeStore';
    import {formatDecimalForDisplay} from '$lib/utils/formatDecimal';
    import {formatCurrencyAmountPlain} from '$lib/utils/currencyFormat';

    // =========================================================================
    // Types
    // =========================================================================

    export type WacMode = 'auto' | 'manual';

    export interface WacPreviewResult {
        wac: {code: string; amount: string} | null;
        qualifying_txs: Array<{
            tx_id: number | null;
            type: string;
            date: string;
            quantity: string;
            unit_cost: string | null;
            currency: string | null;
            effect: string;
            is_pending?: boolean;
        }>;
        missing_pairs: string[];
        asset_price: {code: string; amount: string} | null;
        asset_price_stale: {actual_rate_date: string; days_back: number} | null;
        asset_price_missing: boolean;
    }

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        /** Current cost_basis_override value (bound to form draft) */
        value: {code: string; amount: string} | null;
        /** Called when value changes (from auto-fill or manual edit) */
        onChange: (v: {code: string; amount: string} | null) => void;
        /** "auto-new" for new TXs with toggle, "saved" for edit mode with [↺] */
        variant: 'auto-new' | 'saved';
        /** Default currency code for the input */
        defaultCode?: string;
        /** Whether the field is disabled */
        disabled?: boolean;
        /** data-testid prefix */
        testid?: string;

        // WAC computation params (caller provides these):
        /** Sender broker ID for WAC calculation */
        senderBrokerId?: number | null;
        /** Asset ID */
        assetId?: number | null;
        /** Date for WAC calculation (end of range) */
        txDate?: string | null;
        /** Pending TXs from workspace (TXCreateItem format + id) */
        pendingTxs?: Array<Record<string, any>>;
        /** Excluded TX IDs (deleted in workspace) */
        excludedTxIds?: number[];
    }

    let {value, onChange, variant, defaultCode = 'EUR', disabled = false, testid = 'wac-preview', senderBrokerId = null, assetId = null, txDate = null, pendingTxs = [], excludedTxIds = []}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let mode = $state<WacMode>(initialMode());
    let loading = $state(false);

    function initialMode(): WacMode {
        return variant === 'auto-new' ? 'auto' : 'manual';
    }
    let previewResult = $state<WacPreviewResult | null>(null);
    let error = $state<string | null>(null);
    let showQualifying = $state(false);
    let recalcResult = $state<WacPreviewResult | null>(null); // for "saved" variant on-demand recalc

    // Abort controller for cancelling in-flight requests
    let abortController: AbortController | null = null;

    // =========================================================================
    // Derived
    // =========================================================================

    let isAuto = $derived(mode === 'auto');
    let hasMissingPairs = $derived((previewResult?.missing_pairs?.length ?? 0) > 0);
    let qualifyingCount = $derived(previewResult?.qualifying_txs?.length ?? 0);

    // =========================================================================
    // Auto-fetch WAC preview (debounced)
    // =========================================================================

    let debounceTimer: ReturnType<typeof setTimeout> | null = null;

    $effect(() => {
        // Dependencies: re-run when these change
        const _broker = senderBrokerId;
        const _asset = assetId;
        const _date = txDate;
        const _pending = pendingTxs;
        const _excluded = excludedTxIds;

        if (mode !== 'auto' || variant !== 'auto-new') return;
        if (!_broker || !_asset || !_date) {
            previewResult = null;
            return;
        }

        // Debounce: 500ms trailing
        if (debounceTimer) clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            fetchWacPreview(_broker, _asset, _date, _pending, _excluded);
        }, 500);

        return () => {
            if (debounceTimer) clearTimeout(debounceTimer);
        };
    });

    // =========================================================================
    // Fetch WAC Preview
    // =========================================================================

    async function fetchWacPreview(brokerId: number, assetId: number, date: string, pending: Array<Record<string, any>>, excluded: number[]) {
        // Cancel previous request
        if (abortController) abortController.abort();
        abortController = new AbortController();

        loading = true;
        error = null;

        try {
            const resp = await zodiosApi.wac_preview_api_v1_transactions_wac_preview_post(
                {
                    items: [
                        {
                            sender_broker_id: brokerId,
                            asset_id: assetId,
                            date_range: {end: date},
                        },
                    ],
                    pending_txs: pending as any,
                    excluded_tx_ids: excluded,
                },
                {signal: abortController.signal},
            );

            const result = (resp as any)?.items?.[0];
            if (result) {
                previewResult = {
                    wac: result.wac ?? null,
                    qualifying_txs: result.wac_qualifying_txs ?? [],
                    missing_pairs: result.wac_missing_pairs ?? [],
                    asset_price: result.asset_price ?? null,
                    asset_price_stale: result.asset_price_stale ?? null,
                    asset_price_missing: result.asset_price_missing ?? false,
                };

                // Auto-fill the value if in auto mode
                if (mode === 'auto' && previewResult.wac) {
                    onChange(previewResult.wac);
                }
            }
        } catch (e: any) {
            if (e?.name === 'AbortError') return;
            error = e?.message ?? 'WAC preview failed';
        } finally {
            loading = false;
        }
    }

    // =========================================================================
    // Recalculate (for "saved" variant)
    // =========================================================================

    async function handleRecalculate() {
        if (!senderBrokerId || !assetId || !txDate) return;
        loading = true;
        error = null;
        recalcResult = null;

        try {
            const resp = await zodiosApi.wac_preview_api_v1_transactions_wac_preview_post({
                items: [
                    {
                        sender_broker_id: senderBrokerId,
                        asset_id: assetId,
                        date_range: {end: txDate},
                    },
                ],
                pending_txs: pendingTxs as any,
                excluded_tx_ids: excludedTxIds,
            });

            const result = (resp as any)?.items?.[0];
            if (result) {
                recalcResult = {
                    wac: result.wac ?? null,
                    qualifying_txs: result.wac_qualifying_txs ?? [],
                    missing_pairs: result.wac_missing_pairs ?? [],
                    asset_price: result.asset_price ?? null,
                    asset_price_stale: result.asset_price_stale ?? null,
                    asset_price_missing: result.asset_price_missing ?? false,
                };
            }
        } catch (e: any) {
            error = e?.message ?? 'Recalculation failed';
        } finally {
            loading = false;
        }
    }

    function acceptRecalculated() {
        if (recalcResult?.wac) {
            onChange(recalcResult.wac);
            recalcResult = null;
        }
    }

    function dismissRecalc() {
        recalcResult = null;
    }

    // =========================================================================
    // Toggle handlers
    // =========================================================================

    function setAutoMode() {
        mode = 'auto';
        // Re-trigger fetch by touching dependencies naturally via $effect
    }

    function switchToManual() {
        mode = 'manual';
        if (abortController) abortController.abort();
    }

    /** Called when user types in the amount field — auto-switch to manual */
    function handleValueChange(next: {code: string; amount: string} | null) {
        if (mode === 'auto' && variant === 'auto-new') {
            mode = 'manual';
        }
        onChange(next);
    }
</script>

<!-- =========================================================================
     TEMPLATE
     ========================================================================= -->

<div class="flex flex-col gap-1.5" data-testid={testid}>
    <!-- Label row with toggle -->
    <div class="flex items-center gap-2">
        <span class="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap flex items-center gap-1">
            {$t('transactions.form.costBasis')}
            <Tooltip text={$t('transactions.costBasisOverride.tooltip')} position="top">
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-gray-400 dark:text-gray-500"
                    ><circle cx="12" cy="12" r="10" /><path d="M12 16v-4" /><path d="M12 8h.01" /></svg
                >
            </Tooltip>
        </span>

        {#if variant === 'auto-new'}
            <!-- Toggle Auto/Manual -->
            <div class="flex items-center gap-1 text-[10px] ml-auto" data-testid="{testid}-toggle">
                <button type="button" class="px-1.5 py-0.5 rounded {isAuto ? 'bg-libre-green/10 text-libre-green font-medium' : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'}" onclick={setAutoMode} {disabled} data-testid="{testid}-toggle-auto">{$t('transactions.wacPreview.toggleAuto')}</button>
                <span class="text-gray-300 dark:text-gray-600">|</span>
                <button type="button" class="px-1.5 py-0.5 rounded {!isAuto ? 'bg-gray-200 dark:bg-slate-700 text-gray-700 dark:text-gray-200 font-medium' : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'}" onclick={switchToManual} {disabled} data-testid="{testid}-toggle-manual"
                    >{$t('transactions.wacPreview.toggleManual')}</button
                >
            </div>
        {/if}
    </div>

    <!-- Input field -->
    <div class="flex items-center gap-2 {isAuto && previewResult?.wac ? 'opacity-60 italic' : ''}">
        <CompactCashCell {value} onChange={handleValueChange} signHint="positive" amountPlaceholder={isAuto ? 'auto' : '0.00'} {defaultCode} {disabled} testid="{testid}-input" />

        {#if variant === 'saved' && !disabled}
            <button type="button" class="p-1 rounded hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300" onclick={handleRecalculate} title={$t('transactions.wacPreview.recalculate') ?? 'Recalculate'} data-testid="{testid}-recalculate">
                <RefreshCw size={14} class={loading ? 'animate-spin' : ''} />
            </button>
        {/if}

        {#if loading && variant === 'auto-new'}
            <span class="text-[10px] text-gray-400 animate-pulse" data-testid="{testid}-loading">
                {$t('transactions.wacPreview.calculating') ?? 'Calculating...'}
            </span>
        {/if}
    </div>

    <!-- Auto mode: suggestion info + foldable qualifying panel -->
    {#if variant === 'auto-new' && isAuto && previewResult && !hasMissingPairs && previewResult.wac}
        <div class="flex items-center gap-1 text-[10px] text-gray-500 dark:text-gray-400" data-testid="{testid}-suggestion">
            <Lightbulb size={12} class="text-amber-500 shrink-0" />
            <button type="button" class="flex items-center gap-0.5 hover:text-gray-700 dark:hover:text-gray-200" onclick={() => (showQualifying = !showQualifying)} data-testid="{testid}-show-qualifying">
                {#if showQualifying}
                    <ChevronDown size={10} />
                {:else}
                    <ChevronRight size={10} />
                {/if}
                <span>
                    {$t('transactions.wacPreview.suggested') ?? 'Suggested WAC'}
                    ({qualifyingCount}
                    {$t('transactions.wacPreview.txsUsed') ?? 'transactions used'})
                </span>
            </button>
            <DocsLink path="financial-theory/portfolio-theory/weighted-average-cost/" label={$t('transactions.wacPreview.docsTooltip') ?? 'Learn how WAC (Weighted Average Cost) is calculated'} size={11} />
        </div>
    {/if}

    <!-- Missing FX pairs error -->
    {#if hasMissingPairs}
        <div class="flex flex-col gap-1.5 text-[10px] text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/10 rounded p-2" data-testid="{testid}-missing-pairs">
            <div class="flex items-start gap-1">
                <AlertTriangle size={12} class="mt-0.5 shrink-0" />
                <div>
                    <p class="font-medium">{$t('transactions.wacPreview.missingFx') ?? 'Cannot calculate WAC: missing FX rate'}</p>
                    {#each previewResult?.missing_pairs ?? [] as pair}
                        <p class="text-gray-500">{pair}</p>
                    {/each}
                </div>
            </div>
            <div class="flex flex-wrap gap-1.5 ml-4">
                <a href="/fx" class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 hover:bg-amber-200 no-underline" data-testid="{testid}-action-add-fx">
                    {$t('transactions.wacPreview.addFxPair') ?? 'Add FX pair →'}
                </a>
                <button type="button" class="px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 hover:bg-amber-200" data-testid="{testid}-action-sync-fx">
                    {$t('transactions.wacPreview.syncFx') ?? 'Sync FX rates'}
                </button>
                <button type="button" class="px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 hover:bg-amber-200" data-testid="{testid}-action-sync-prices">
                    {$t('transactions.wacPreview.syncPrices') ?? 'Sync asset prices'}
                </button>
            </div>
        </div>
    {/if}

    <!-- Error -->
    {#if error}
        <p class="text-[10px] text-red-500" data-testid="{testid}-error">{error}</p>
    {/if}

    <!-- Qualifying TXs table (expandable) -->
    {#if showQualifying && previewResult?.qualifying_txs?.length}
        <div class="mt-1 max-h-40 w-0 min-w-full overflow-x-auto overflow-y-auto border border-gray-200 dark:border-slate-700 rounded text-[10px] scrollbar-thin scrollbar-thumb-gray-300 dark:scrollbar-thumb-slate-600" data-testid="{testid}-qualifying-table">
            <table class="w-max min-w-full">
                <thead class="bg-gray-50 dark:bg-slate-800 sticky top-0">
                    <tr>
                        <th class="px-2 py-1 text-left min-w-[28px]">#</th>
                        <th class="px-2 py-1 text-left min-w-[120px]">{$t('transactions.table.type')}</th>
                        <th class="px-2 py-1 text-left min-w-[90px]">{$t('transactions.table.date')}</th>
                        <th class="px-2 py-1 text-right min-w-[35px]">{$t('transactions.table.quantity')}</th>
                        <th class="px-2 py-1 text-right min-w-[120px]">{$t('transactions.wacPreview.unitCost') ?? 'Unit'}</th>
                        <th class="px-2 py-1 text-left min-w-[140px]">{$t('transactions.wacPreview.effectLabel') ?? 'Effect'}</th>
                    </tr>
                </thead>
                <tbody>
                    {#each previewResult.qualifying_txs as qtx}
                        <tr class="border-t border-gray-100 dark:border-slate-800 {qtx.tx_id == null ? 'bg-indigo-50/50 dark:bg-indigo-900/10' : ''}">
                            <td class="px-2 py-0.5">{qtx.tx_id ?? '●'}</td>
                            <td class="px-2 py-0.5">
                                <span class="inline-flex items-center gap-1">
                                    {#if getTransactionTypeIconUrl(qtx.type)}
                                        <img src={getTransactionTypeIconUrl(qtx.type)} alt="" class="w-3 h-3 object-contain" />
                                    {/if}
                                    <span>{$t(`transactions.types.${qtx.type}`) ?? qtx.type}</span>
                                </span>
                            </td>
                            <td class="px-2 py-0.5">{qtx.date}</td>
                            <td class="px-2 py-0.5 text-right font-mono">{formatDecimalForDisplay(qtx.quantity)}</td>
                            <td class="px-2 py-0.5 text-right font-mono">{qtx.unit_cost && qtx.currency ? formatCurrencyAmountPlain(parseFloat(qtx.unit_cost), qtx.currency, {maxFraction: 2}) : qtx.unit_cost ? parseFloat(qtx.unit_cost).toFixed(2) : '—'}</td>
                            <td class="px-2 py-0.5">
                                <span
                                    class="inline-block px-1 rounded text-[9px] {qtx.effect === 'add'
                                        ? 'bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400'
                                        : qtx.effect === 'reduce'
                                          ? 'bg-amber-100 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400'
                                          : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'}"
                                    >{qtx.effect === 'add'
                                        ? ($t('transactions.wacPreview.effect.add') ?? 'Weighted')
                                        : qtx.effect === 'reduce'
                                          ? ($t('transactions.wacPreview.effect.reduce') ?? 'Reduced')
                                          : ($t('transactions.wacPreview.effect.addZeroCost') ?? 'Dilution')}</span
                                >
                            </td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>
    {/if}

    <!-- Recalculate result panel (for "saved" variant) -->
    {#if recalcResult}
        <div class="mt-1 p-2 border border-indigo-200 dark:border-indigo-800 rounded bg-indigo-50/50 dark:bg-indigo-900/10 text-[10px]" data-testid="{testid}-recalc-panel">
            {#if recalcResult.wac}
                <p class="font-medium text-indigo-700 dark:text-indigo-300">
                    📊 {$t('transactions.wacPreview.recalculated') ?? 'Recalculated'}: {recalcResult.wac.amount}
                    {recalcResult.wac.code}
                    {#if value}
                        <span class="text-gray-400">(was: {value.amount} {value.code})</span>
                    {/if}
                </p>
                <div class="flex gap-2 mt-1">
                    <button type="button" class="px-2 py-0.5 rounded bg-indigo-600 text-white hover:bg-indigo-700 text-[10px]" onclick={acceptRecalculated} data-testid="{testid}-accept-recalc">{$t('transactions.wacPreview.accept') ?? 'Accept'} {recalcResult.wac.amount}</button>
                    <button type="button" class="px-2 py-0.5 rounded bg-gray-200 dark:bg-slate-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 text-[10px]" onclick={dismissRecalc} data-testid="{testid}-keep-current">{$t('transactions.wacPreview.keep') ?? 'Keep current'}</button>
                </div>
            {:else if recalcResult.missing_pairs.length > 0}
                <p class="text-amber-600 dark:text-amber-400">
                    <AlertTriangle size={10} class="inline" />
                    {$t('transactions.wacPreview.missingFx') ?? 'Missing FX rate'}: {recalcResult.missing_pairs.join(', ')}
                </p>
            {:else}
                <p class="text-gray-500">{$t('transactions.wacPreview.noData') ?? 'No qualifying transactions found'}</p>
            {/if}
        </div>
    {/if}
</div>
