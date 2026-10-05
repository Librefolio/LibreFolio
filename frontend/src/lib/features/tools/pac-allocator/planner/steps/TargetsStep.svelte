<script lang="ts">
    import {PieChart, Scale} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import DataTableToolbar from '$lib/components/table/DataTableToolbar.svelte';
    import type {ColumnDef, RowAction} from '$lib/components/table/types';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {canonicalInput, compareDecimal, decimalSign, rebalanceControlPercentages, remainingControlPercentage, sumControlPercentages} from '../decimal';
    import type {DraftAsset, PlannerDraft} from '../draft.svelte';
    import {formatPlannerPercentUnits} from '../format';
    import {BUTTON_SECONDARY, NOTICE} from '../ui';
    import AssetNameCell from '../shared/AssetNameCell.svelte';
    import HelpTip from '../shared/HelpTip.svelte';
    import TargetInputCell from '../shared/TargetInputCell.svelte';
    import TableColumns from '../shared/TableColumns.svelte';
    import {withHelpCues} from '../shared/columnHelp';
    import DistributionDialog from './DistributionDialog.svelte';

    interface Props {
        draft: PlannerDraft;
        accountGeneration: number;
    }

    let {draft, accountGeneration}: Props = $props();

    const KEY = 'tools.pacAllocator.planner.targets';
    type TotalState = 'balanced' | 'excess' | 'missing' | 'unknown';
    /** Colours of the Asset distribution editor: green at 100%, red above, amber below. */
    const BAR_CLASS: Record<TotalState, string> = {balanced: 'bg-libre-green', excess: 'bg-red-400', missing: 'bg-amber-400', unknown: 'bg-gray-300 dark:bg-gray-600'};
    const TOTAL_CLASS: Record<TotalState, string> = {balanced: 'text-green-600 dark:text-green-400', excess: 'text-red-500', missing: 'text-amber-500', unknown: 'text-gray-500 dark:text-gray-400'};

    let copying = $state(false);
    let selectedKeys = $state<string[]>([]);
    let tableRef: DataTable<DraftAsset> | undefined = $state(undefined);

    const copyDisabled = $derived(!/^[A-Z]{3}$/.test(draft.data.valuationCurrency) || !draft.data.assets.some((asset) => asset.sourceAssetId !== null));
    const total = $derived(draft.targetTotal);
    const remaining = $derived(draft.targetRemaining);
    const totalState = $derived.by((): TotalState => {
        const sign = remaining === null ? null : decimalSign(remaining);
        if (sign === 0) return 'balanced';
        if (sign === -1) return 'excess';
        if (sign === 1) return 'missing';
        return 'unknown';
    });
    const excess = $derived(remaining === null ? null : remainingControlPercentage(remaining, '0'));
    const maxWeight = $derived(Math.max(1, ...draft.data.assets.map((asset) => percentNumber(draft.data.targets[asset.key]))));

    function assetLabel(asset: DraftAsset): string {
        return [asset.ticker, asset.name].filter((part) => part.trim() !== '').join(' ');
    }

    /** Bar length only: a picture of the target, never a value that is sent. */
    function percentNumber(value: string | undefined): number {
        const canonical = canonicalInput(value ?? '');
        const number = canonical === null ? 0 : Number(canonical);
        return Number.isFinite(number) ? Math.max(0, number) : 0;
    }

    function barHtml(asset: DraftAsset): string {
        const width = Math.min(100, (percentNumber(draft.data.targets[asset.key]) / maxWeight) * 100);
        return `<div data-testid="pac-planner-target-bar" data-asset-key="${escapeHtml(asset.key)}" aria-hidden="true" class="h-3 overflow-hidden rounded-full bg-gray-100 dark:bg-slate-700"><div class="h-full rounded-full transition-all ${escapeHtml(BAR_CLASS[totalState])}" style="width: ${width}%"></div></div>`;
    }

    /** Gives this Asset what is missing, or takes away the excess, within 0–100. */
    function balance(asset: DraftAsset): void {
        if (remaining === null) return;
        const next = sumControlPercentages([canonicalInput(draft.data.targets[asset.key] ?? '') ?? '0', remaining]);
        if (next === null) return;
        if ((compareDecimal(next, '0') ?? 0) < 0) draft.data.targets[asset.key] = '0';
        else if ((compareDecimal(next, '100') ?? 0) > 0) draft.data.targets[asset.key] = '100';
        else draft.data.targets[asset.key] = next;
    }

    /** Targets in row order; an empty field counts as 0, text that is not a number stops the balancing. */
    const controlValues = $derived(draft.orderedAssets.map((asset) => ((draft.data.targets[asset.key] ?? '').trim() === '' ? '0' : canonicalInput(draft.data.targets[asset.key]))));
    const selectedIndices = $derived.by(() => {
        const keys = new Set(selectedKeys);
        return draft.orderedAssets.flatMap((asset, index) => (keys.has(asset.key) ? [index] : []));
    });

    /** Rescales the chosen rows, keeping their ratios, so the total is exactly 100% (equal parts if they are all 0). */
    function rebalanced(indices: readonly number[]): string[] | null {
        if (totalState === 'balanced' || controlValues.some((value) => value === null)) return null;
        return rebalanceControlPercentages(controlValues as string[], indices);
    }

    const canBalanceAll = $derived(draft.orderedAssets.length > 0 && rebalanced(draft.orderedAssets.map((_, index) => index)) !== null);
    const canBalanceSelected = $derived(selectedIndices.length > 0 && rebalanced(selectedIndices) !== null);

    function applyBalance(indices: readonly number[]): void {
        const next = rebalanced(indices);
        if (next === null) return;
        for (const index of indices) draft.data.targets[draft.orderedAssets[index].key] = next[index];
    }

    function balanceSelected(): void {
        applyBalance(selectedIndices);
        tableRef?.clearSelection();
    }

    const columns = $derived.by((): ColumnDef<DraftAsset>[] => withHelpCues<DraftAsset>([
        {
            id: 'asset',
            header: () => $t('tools.pacAllocator.planner.routing.asset', {default: 'Asset'}),
            type: 'text',
            sortable: false,
            filterable: false,
            minWidth: 160,
            getValue: (asset) => assetLabel(asset),
            cell: (asset) => ({type: 'custom', component: AssetNameCell, props: {label: assetLabel(asset), iconUrl: asset.iconUrl, assetType: asset.assetClass ? asset.assetClass.toUpperCase() : null}}),
        },
        {
            id: 'bar',
            header: () => $t(`${KEY}.shape`, {default: 'Distribution'}),
            type: 'custom',
            sortable: false,
            filterable: false,
            width: 200,
            minWidth: 100,
            cell: (asset) => ({type: 'html', html: barHtml(asset)}),
        },
        {
            id: 'target',
            header: () => $t(`${KEY}.target`, {default: 'Target %'}),
            headerTooltip: () => $t(`${KEY}.wire`, {default: 'The share of the money you invest now that goes to this Asset, in percent. Decimals are allowed.'}),
            type: 'custom',
            sortable: false,
            filterable: false,
            align: 'right',
            width: 140,
            minWidth: 128,
            cell: (asset) => ({type: 'custom', component: TargetInputCell, props: {draft, assetKey: asset.key, label: assetLabel(asset)}}),
        },
    ]));

    const rowActions = $derived.by((): RowAction<DraftAsset>[] => [
        {
            id: 'balance',
            icon: Scale,
            label: () => $t(`${KEY}.balance`, {default: 'Balance to 100%'}),
            onClick: (asset) => balance(asset),
            disabled: () => totalState === 'balanced' || totalState === 'unknown',
            testid: 'pac-planner-target-balance',
        },
    ]);
</script>

<div class="space-y-3" data-testid="pac-planner-targets">
    <div class="flex flex-wrap items-center gap-2">
        <p class="text-sm text-gray-700 dark:text-gray-300">{$t(`${KEY}.intro`, {default: 'How to split among the Assets the money you invest now, in percent.'})}</p>
        <div class="ml-auto flex flex-wrap items-center justify-end gap-1.5">
            {#if selectedKeys.length > 0}
                <DataTableToolbar
                    selectedCount={selectedKeys.length}
                    bulkActions={[
                        {
                            id: 'balance-selected',
                            icon: Scale,
                            label: () => $t(`${KEY}.balanceSelected`, {default: 'Balance the selected rows to 100%'}),
                            onClick: balanceSelected,
                            disabled: !canBalanceSelected,
                        },
                    ]}
                    onClearSelection={() => tableRef?.clearSelection()}
                />
            {/if}
            {#if draft.data.assets.length > 0}
                <button type="button" class={BUTTON_SECONDARY} disabled={!canBalanceAll} data-testid="pac-planner-targets-balance-all" onclick={() => applyBalance(draft.orderedAssets.map((_, index) => index))}>
                    <Scale class="h-4 w-4" aria-hidden="true" />
                    {$t(`${KEY}.balanceAll`, {default: 'Balance all'})}
                </button>
            {/if}
            <div class="flex items-center gap-0.5">
                <button type="button" class={BUTTON_SECONDARY} disabled={copyDisabled} data-testid="pac-planner-distribution-open" onclick={() => (copying = true)}>
                    <PieChart class="h-4 w-4" aria-hidden="true" />
                    {$t(`${KEY}.copyDistribution`, {default: 'Copy current distribution'})}
                </button>
                <HelpTip
                    label={$t(`${KEY}.copyDistribution`, {default: 'Copy current distribution'})}
                    help={$t(`${KEY}.copyHelp`, {default: 'Reads how much each of these Assets weighs today in the Brokers you tick, counting only these Assets and not the cash, and brings the ratios to 100%. Assets entered by hand get 0. You see the weights before using them, and a target you changed is replaced only after you confirm.'})}
                    testid="pac-planner-distribution-help"
                />
            </div>
            {#if draft.data.assets.length > 0}
                <TableColumns table={tableRef} testid="pac-planner-targets-columns" />
            {/if}
        </div>
    </div>

    {#if draft.data.assets.length === 0}
        <p class={NOTICE.info} data-testid="pac-planner-targets-empty">{$t('tools.pacAllocator.planner.problems.noAssets', {default: 'Add at least one Asset.'})}</p>
    {:else}
        <div data-testid="pac-planner-targets-table">
            <DataTable
                bind:this={tableRef}
                data={draft.orderedAssets}
                {columns}
                getRowId={(asset) => asset.key}
                storageKey="pac-planner-targets"
                enableSorting={false}
                enablePagination={false}
                enableSelection
                selectionMode="multi"
                onSelectionChange={(ids) => (selectedKeys = ids)}
                enableColumnVisibility
                enableColumnFilters={false}
                enableColumnResize
                enableContextMenu={false}
                enableActions
                {rowActions}
                actionsColumnWidth="64px"
                tableLayout="auto"
            />
        </div>

        <div class="flex flex-wrap items-center justify-end gap-1.5 pt-1 text-xs font-medium" data-testid="pac-planner-targets-control" data-balanced={totalState === 'balanced' ? 'true' : 'false'} data-state={totalState}>
            <span class="text-gray-500 dark:text-gray-400">{$t(`${KEY}.total`, {default: 'Total'})}</span>
            <span class="font-mono {TOTAL_CLASS[totalState]}" data-testid="pac-planner-targets-total">{total === null ? '—' : formatPlannerPercentUnits(total)}</span>
            {#if totalState === 'balanced'}
                <span class="text-green-500" aria-hidden="true">✅</span>
            {:else if totalState === 'excess' && excess !== null}
                <span class="text-red-500">⚠ {$t(`${KEY}.excess`, {default: '+{value} in excess', values: {value: formatPlannerPercentUnits(excess)}})}</span>
            {:else if totalState === 'missing' && remaining !== null}
                <span class="text-amber-500">⚠ {$t(`${KEY}.remaining`, {default: '{value} missing', values: {value: formatPlannerPercentUnits(remaining)}})}</span>
            {/if}
            <HelpTip
                label={$t(`${KEY}.total`, {default: 'Total'})}
                help={$t(`${KEY}.totalHelp`, {default: 'The targets split among the Assets the money you invest now, cash and contributions included: to calculate, they must add up to exactly 100%. «Balance all» rescales every target keeping their ratios (equal parts if they are all 0). Tick some rows to rescale only those, with «Balance the selected rows to 100%». «Balance to 100%» on a row gives that Asset what is missing, or takes away the excess.'})}
                testid="pac-planner-targets-total-help"
            />
        </div>
    {/if}
</div>

{#if copying}
    <DistributionDialog {draft} {accountGeneration} onclose={() => (copying = false)} />
{/if}
