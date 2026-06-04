<script lang="ts">
    /**
     * WacPreviewSection — WAC preview with Auto/Manual toggle for cost_basis_override.
     *
     * Used in: TransactionFormModal (TRANSFER + ADJUSTMENT), BulkModal cells, PromoteMergeModal.
     *
     * The Auto/Manual toggle is always visible. In Auto mode, the WAC value is
     * provided externally via `externalResult` (from validate response).
     * In Manual mode, the user types a value directly.
     *
     * **Controlled component**: `mode` is owned by the parent. The component calls
     * `onModeChange` when the user clicks a toggle button; the parent decides
     * whether to accept the change.
     */
    import {t} from 'svelte-i18n';
    import {ChevronDown, ChevronRight, Lightbulb, AlertTriangle} from 'lucide-svelte';
    import CompactCashCell from '$lib/components/ui/CompactCashCell.svelte';
    import Tooltip from '$lib/components/ui/Tooltip.svelte';
    import DocsLink from '$lib/components/ui/DocsLink.svelte';
    import {getTransactionTypeIconUrl} from '$lib/stores/transactionTypeStore';
    import {formatDecimalForDisplay} from '$lib/utils/formatDecimal';
    import {formatCurrencyAmountPlain, formatCurrencyCodeHtml} from '$lib/utils/currencyFormat';

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
            running_wac?: string | null;
            is_pending?: boolean;
            pending_op?: string;
            fx_info?: {fx_rate_date: string | null; fx_days_back: number | null} | null;
            original_unit_cost?: string | null;
            original_currency?: string | null;
            fx_rate_used?: string | null;
        }>;
        missing_pairs: Array<{pair: string; dates: string[]} | string>;
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
        /** Controlled mode — parent owns this state */
        mode: 'auto' | 'manual';
        /** Default currency code for the input */
        defaultCode?: string;
        /** Whether the field is disabled */
        disabled?: boolean;
        /** data-testid prefix */
        testid?: string;

        // WAC computation params (kept for API compat but unused — WAC comes from externalResult):
        /** Sender broker ID for WAC calculation */
        senderBrokerId?: number | null;
        /** Asset ID */
        assetId?: number | null;
        /** Date for WAC calculation (end of range) */
        txDate?: string | null;
        /** Pending TXs from workspace (unused — kept for API compat) */
        pendingTxs?: Array<Record<string, any>>;
        /** Excluded TX IDs (unused — kept for API compat) */
        excludedTxIds?: number[];
        /** Hide qualifying table (e.g. in view-only mode) */
        hideTable?: boolean;
        /** Called when mode changes (auto ↔ manual) — for parent propagation */
        onModeChange?: (mode: 'auto' | 'manual') => void;
        /** External WAC result from parent (validate response or BulkModal).
         *  When non-null and mode is 'auto', this data is displayed directly. */
        externalResult?: {wac: {code: string; amount: string} | null; qualifying_txs: Array<Record<string, any>>; missing_pairs: Array<{pair: string; dates: string[]} | string>} | null;
        /** Set of TX IDs that are pending (batch-created, not yet committed).
         *  Used to annotate qualifying table rows with pending indicator at render time. */
        pendingTxIds?: Set<number> | null;
        /** Current WAC currency (from hint or response) */
        wacCurrency?: string | null;
        /** Called when user changes currency via chip */
        onCurrencyChange?: (code: string) => void;
        /** Available currencies for the chip dropdown */
        availableCurrencies?: string[];
    }

    let {value, onChange, mode, defaultCode = 'EUR', disabled = false, testid = 'wac-preview', senderBrokerId = null, assetId = null, txDate = null, pendingTxs = [], excludedTxIds = [], hideTable = false, onModeChange, externalResult = null, pendingTxIds = null, wacCurrency = null, onCurrencyChange, availableCurrencies = []}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let loading = $state(false);

    let previewResult = $state<WacPreviewResult | null>(null);
    let error = $state<string | null>(null);
    let showQualifying = $state(false);

    // Reset qualifying table visibility when mode switches to manual
    $effect(() => {
        if (mode === 'manual') showQualifying = false;
    });

    // NOTE: missing_pairs no longer forces manual — user stays in auto, sees error banner

    // =========================================================================
    // Derived
    // =========================================================================

    let isAuto = $derived(mode === 'auto');
    let hasMissingPairs = $derived((previewResult?.missing_pairs?.length ?? 0) > 0);
    let qualifyingCount = $derived(previewResult?.qualifying_txs?.length ?? 0);
    let maxFxStaleDays = $derived(previewResult?.qualifying_txs?.reduce((max, qtx) => Math.max(max, qtx.fx_info?.fx_days_back ?? 0), 0) ?? 0);
    let hasStaleFx = $derived(maxFxStaleDays > 5);
    // NOTE: hasMissingPairs no longer forces manual — only shows error banner
    let forcedManual = false; // kept for template compat, always false
    let hasAnyFxConversion = $derived(previewResult?.qualifying_txs?.some((q) => q.fx_info != null) ?? false);
    /** True when the user changed currency but the result hasn't caught up yet */
    let currencyPending = $derived(
        isAuto && wacCurrency != null && previewResult?.wac != null && previewResult.wac.code !== wacCurrency,
    );

    // =========================================================================
    // External result sync — WAC data from validate response
    // =========================================================================

    $effect(() => {
        if (!externalResult) return;
        previewResult = {
            wac: externalResult.wac,
            qualifying_txs: (externalResult.qualifying_txs as any) ?? [],
            missing_pairs: externalResult.missing_pairs ?? [],
            asset_price: null,
            asset_price_stale: null,
            asset_price_missing: false,
        };
        loading = false;
        if (mode === 'auto' && externalResult.wac) {
            const next = externalResult.wac;
            if (!value || value.code !== next.code || value.amount !== next.amount) {
                onChange(next);
            }
        }
    });

    // =========================================================================
    // Toggle handlers
    // =========================================================================

    function setAutoMode() {
        onModeChange?.('auto');
        // If external result already has a value, apply it immediately
        if (externalResult?.wac) {
            const next = externalResult.wac;
            if (!value || value.code !== next.code || value.amount !== next.amount) {
                onChange(next);
            }
        }
    }

    function switchToManual() {
        onModeChange?.('manual');
    }

    /** Called when user types in the amount field — auto-switch to manual.
     *  In auto mode: currency change → WAC currency override; amount change → switch to manual. */
    function handleValueChange(next: {code: string; amount: string} | null) {
        if (!next) {
            onChange(next);
            return;
        }

        if (mode === 'auto') {
            const prevCode = value?.code;
            // Currency changed (but only if we had a previous code) → WAC currency override (stay in auto)
            if (prevCode != null && next.code !== prevCode) {
                onCurrencyChange?.(next.code);
                return;
            }
            // Amount changed EFFECTIVELY → switch to manual
            const currentAmount = value?.amount ?? '';
            if (next.amount === currentAmount) return; // blur without modification → no-op
            onModeChange?.('manual');
        }
        onChange(next);
    }

    // =========================================================================
    // FX tooltip helpers
    // =========================================================================

    type QtxRow = WacPreviewResult['qualifying_txs'][number];

    function buildFxTooltipHtml(qtx: QtxRow): string {
        if (!qtx.fx_info || !qtx.original_currency || !qtx.currency) return '';
        const rate = qtx.fx_rate_used ? parseFloat(qtx.fx_rate_used).toFixed(4) : '?';
        const fromHtml = formatCurrencyCodeHtml(qtx.original_currency);
        const toHtml = formatCurrencyCodeHtml(qtx.currency);
        const date = qtx.fx_info.fx_rate_date ?? '?';
        const days = qtx.fx_info.fx_days_back ?? 0;
        const staleNote = days > 5 ? `<br/><span class="text-amber-500">⚠️ ${$t('transactions.wac.fxTooltipStale') || 'Rate not up to date'}</span>` : '';
        return `↳ Rate: ${rate}<br/>${fromHtml} → ${toHtml}<br/>${$t('transactions.wac.fxTooltipDate') || 'Rate date'}: ${date} (${days}${$t('transactions.wac.fxDaysAgo') || 'd ago'})${staleNote}`;
    }

    function buildBadgeTooltipHtml(): string {
        const disclaimer = $t('transactions.wac.fxDisclaimer') || 'The FX rate used may differ from the one applied by your broker. Verify the average cost with your broker.';
        const pairs = [...new Set((previewResult?.qualifying_txs ?? []).filter((q) => q.original_currency && q.currency && q.original_currency !== q.currency).map((q) => `${formatCurrencyCodeHtml(q.original_currency!)} → ${formatCurrencyCodeHtml(q.currency!)}`))];
        const pairsHtml = pairs.length > 0 ? `<br/><br/><b>${$t('transactions.wac.convertedPairs') || 'Converted pairs'}:</b><ul class="list-disc pl-4 mt-1">${pairs.map((p) => `<li>${p}</li>`).join('')}</ul>` : '';
        return `${disclaimer}${pairsHtml}`;
    }

    /** Unique stale pairs for the stale banner */
    let stalePairs = $derived([
        ...new Map(
            (previewResult?.qualifying_txs ?? [])
                .filter((q) => q.fx_info && (q.fx_info.fx_days_back ?? 0) > 5 && q.original_currency && q.currency)
                .map((q) => [`${q.original_currency}/${q.currency}`, {from: q.original_currency!, to: q.currency!, date: q.fx_info!.fx_rate_date ?? '?', days: q.fx_info!.fx_days_back ?? 0}] as const),
        ).values(),
    ]);
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
            {#if hasAnyFxConversion}
                <Tooltip html={buildBadgeTooltipHtml()} position="top">
                    <span class="text-[9px] px-1 py-0.5 rounded bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 font-medium cursor-help">💱 FX</span>
                </Tooltip>
            {/if}
        </span>

        <!-- Toggle Auto/Manual — always visible -->
        {#if !disabled}
            <div class="flex items-center gap-1 text-[10px] ml-auto" data-testid="{testid}-toggle">
                <button type="button" class="px-1.5 py-0.5 rounded {isAuto && !forcedManual ? 'bg-libre-green/10 text-libre-green font-medium' : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'}" onclick={setAutoMode} disabled={disabled || forcedManual} data-testid="{testid}-toggle-auto"
                    >{$t('transactions.wacPreview.toggleAuto')}{forcedManual ? ' ⚠️' : ''}</button
                >
                <span class="text-gray-300 dark:text-gray-600">|</span>
                <button
                    type="button"
                    class="px-1.5 py-0.5 rounded {!isAuto || forcedManual ? 'bg-gray-200 dark:bg-slate-700 text-gray-700 dark:text-gray-200 font-medium' : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'}"
                    onclick={switchToManual}
                    {disabled}
                    data-testid="{testid}-toggle-manual">{$t('transactions.wacPreview.toggleManual')}</button
                >
            </div>
        {/if}
    </div>

    <!-- Input field -->
    <div class="flex items-center gap-2">
        <CompactCashCell {value} onChange={handleValueChange} signHint="positive" amountPlaceholder={isAuto ? 'auto' : '0.00'} {defaultCode} currencyDisabled={disabled} disabled={disabled} testid="{testid}-input" />

        {#if loading}
            <span class="text-[10px] text-gray-400 animate-pulse" data-testid="{testid}-loading">
                {$t('transactions.wacPreview.calculating') ?? 'Calculating...'}
            </span>
        {/if}
    </div>

    <!-- Currency pending hint -->
    {#if currencyPending && !loading}
        <p class="text-[10px] text-amber-600 dark:text-amber-400 italic" data-testid="{testid}-currency-pending">
            ⏳ {$t('transactions.wacPreview.currencyChanged') ?? 'Currency changed — validating to update…'}
        </p>
    {/if}

    <!-- Auto mode: suggestion info + foldable qualifying panel -->
    {#if isAuto && previewResult && !hasMissingPairs && previewResult.wac}
        <div class="flex items-center gap-1 text-[10px] text-gray-500 dark:text-gray-400" data-testid="{testid}-suggestion">
            <Tooltip text={$t('transactions.wacPreview.validateToRecalculate') ?? 'Validate to recalculate the table'} position="right">
                <Lightbulb size={12} class="text-amber-500 shrink-0 cursor-help" />
            </Tooltip>
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
    {:else if isAuto && !previewResult && !loading && !error}
        <!-- Auto mode: no result yet — hint to validate -->
        <div class="flex items-center gap-1 text-[10px] text-gray-400 dark:text-gray-500" data-testid="{testid}-validate-hint">
            <Lightbulb size={12} class="text-amber-400/70 shrink-0" />
            <span>{$t('transactions.wacPreview.validateHint') ?? 'Complete the fields and validate to calculate WAC'}</span>
        </div>
    {/if}

    <!-- Missing FX pairs error -->
    {#if hasMissingPairs}
        <div class="text-[10px] text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/10 rounded p-2" data-testid="{testid}-missing-pairs">
            <div class="flex items-center gap-1 font-medium mb-1">
                <AlertTriangle size={12} class="shrink-0" />
                <span>{$t('transactions.wacPreview.missingFx') ?? 'Cannot calculate WAC: missing FX rates'}</span>
            </div>
            <ul class="list-disc pl-4 space-y-0.5">
                {#each previewResult?.missing_pairs ?? [] as mp}
                    {@const pairStr = typeof mp === 'string' ? mp : mp.pair}
                    {@const dates = typeof mp === 'string' ? [] : (mp.dates ?? [])}
                    {@const parts = pairStr.split('/')}
                    <li>
                        {@html formatCurrencyCodeHtml(parts[0])} / {@html formatCurrencyCodeHtml(parts[1])} — {$t('transactions.wac.noRateAvailable') || 'no rate available'}
                        {#if dates.length > 0}
                            <span class="text-gray-500 dark:text-gray-400">({dates.length} {dates.length === 1 ? 'date' : 'dates'})</span>
                        {/if}
                    </li>
                {/each}
            </ul>
        </div>
    {/if}

    <!-- Error -->
    {#if error}
        <p class="text-[10px] text-red-500" data-testid="{testid}-error">{error}</p>
    {/if}

    <!-- FX staleness warning banner (above table) -->
    {#if hasStaleFx && isAuto && showQualifying}
        <div class="text-[10px] text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/10 rounded p-2 mt-1" data-testid="{testid}-fx-stale-banner">
            <div class="flex items-center gap-1 font-medium mb-1">
                <AlertTriangle size={10} class="shrink-0" />
                <span>{$t('transactions.wac.fxStaleBannerTitle') || 'FX conversions with stale rates'}</span>
            </div>
            <ul class="list-disc pl-4 space-y-0.5">
                {#each stalePairs as sp}
                    <li>{@html formatCurrencyCodeHtml(sp.from)} / {@html formatCurrencyCodeHtml(sp.to)} — {sp.date} ({sp.days}{$t('transactions.wac.fxDaysAgo') || 'd ago'})</li>
                {/each}
            </ul>
            <p class="mt-1.5 text-[9px] text-amber-600/80 dark:text-amber-500/70 italic">{$t('transactions.wac.fxDisclaimer') || 'The FX rate used may differ from the one applied by your broker. Verify the average cost with your broker.'}</p>
        </div>
    {/if}

    <!-- Qualifying TXs table (expandable) -->
    {#if !hideTable && showQualifying && previewResult?.qualifying_txs?.length}
        <div class="mt-1 max-h-40 w-0 min-w-full overflow-x-auto overflow-y-auto border border-gray-200 dark:border-slate-700 rounded text-[10px] scrollbar-thin scrollbar-thumb-gray-300 dark:scrollbar-thumb-slate-600" data-testid="{testid}-qualifying-table">
            <table class="w-max min-w-full">
                <thead class="bg-gray-50 dark:bg-slate-800 sticky top-0">
                    <tr>
                        <th class="px-2 py-1 text-left min-w-[28px]">#</th>
                        <th class="px-2 py-1 text-left min-w-[120px]">{$t('transactions.table.type')}</th>
                        <th class="px-2 py-1 text-left min-w-[90px]">{$t('transactions.table.date')}</th>
                        <th class="px-2 py-1 text-center min-w-[35px]">{$t('transactions.table.quantity')}</th>
                        <th class="px-2 py-1 text-center min-w-[120px]">{$t('transactions.wacPreview.unitCost') ?? 'Unit'}</th>
                        <th class="px-2 py-1 text-right min-w-[110px]">{$t('transactions.wacPreview.effectLabel') ?? 'Effect'}</th>
                        <th class="px-2 py-1 text-left min-w-[80px]">{$t('transactions.wacPreview.columnWac') ?? 'WAC'}</th>
                    </tr>
                </thead>
                <tbody>
                    {#each previewResult.qualifying_txs as qtx}
                        {@const isPending = qtx.tx_id == null || qtx.is_pending || (pendingTxIds != null && qtx.tx_id != null && pendingTxIds.has(qtx.tx_id))}
                        {@const pendingType = qtx.pending_op === 'update' ? 'update' : pendingTxIds != null && qtx.tx_id != null && pendingTxIds.has(qtx.tx_id) ? 'create' : 'create'}
                        <tr class="border-t border-gray-100 dark:border-slate-800 {isPending ? 'bg-indigo-50/50 dark:bg-indigo-900/10' : ''}">
                            <td class="px-2 py-0.5">
                                {#if isPending}
                                    <Tooltip text={$t(pendingType === 'update' ? 'transactions.wacPreview.pendingEdit' : 'transactions.wacPreview.pendingCreate')} position="right">
                                        <span class="cursor-help text-indigo-500">●</span>
                                    </Tooltip>
                                {:else}
                                    {qtx.tx_id}
                                {/if}
                            </td>
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
                            <td class="px-2 py-0.5 text-right font-mono">
                                {#if qtx.original_unit_cost && qtx.original_currency && qtx.currency && qtx.original_currency !== qtx.currency}
                                    <Tooltip html={buildFxTooltipHtml(qtx)} position="top">
                                        <span class="cursor-help">
                                            {formatCurrencyAmountPlain(parseFloat(qtx.original_unit_cost), qtx.original_currency, {maxFraction: 2})} → {qtx.unit_cost && qtx.currency ? formatCurrencyAmountPlain(parseFloat(qtx.unit_cost), qtx.currency, {maxFraction: 2}) : '?'}
                                            {#if qtx.fx_info && (qtx.fx_info.fx_days_back ?? 0) > 5}
                                                <span class="text-amber-500 ml-0.5">⚠️</span>
                                            {:else}
                                                <span class="text-gray-400 ml-0.5">💱</span>
                                            {/if}
                                        </span>
                                    </Tooltip>
                                {:else}
                                    {qtx.unit_cost && qtx.currency ? formatCurrencyAmountPlain(parseFloat(qtx.unit_cost), qtx.currency, {maxFraction: 2}) : qtx.unit_cost ? parseFloat(qtx.unit_cost).toFixed(2) : '—'}
                                {/if}
                            </td>
                            <td class="px-2 py-0.5 text-right">
                                <span
                                    class="inline-block px-1 rounded text-[9px] {qtx.effect === 'add'
                                        ? 'bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400'
                                        : qtx.effect === 'reduce'
                                          ? 'bg-amber-100 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400'
                                          : qtx.effect === 'add_at_wac'
                                            ? 'bg-indigo-100 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-400'
                                            : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'}"
                                    >{qtx.effect === 'add'
                                        ? ($t('transactions.wacPreview.effect.add') ?? 'Weighted')
                                        : qtx.effect === 'reduce'
                                          ? ($t('transactions.wacPreview.effect.reduce') ?? 'Reduced')
                                          : qtx.effect === 'add_at_wac'
                                            ? ($t('transactions.wacPreview.effect.addAtWac') ?? 'Inherited')
                                            : ($t('transactions.wacPreview.effect.addZeroCost') ?? 'Dilution')}</span
                                >
                            </td>
                            <td class="px-2 py-0.5 text-left font-mono">{qtx.running_wac && qtx.currency ? formatCurrencyAmountPlain(parseFloat(qtx.running_wac), qtx.currency, {maxFraction: 4}) : qtx.running_wac ? parseFloat(qtx.running_wac).toFixed(4) : '—'}</td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>
    {/if}
</div>
