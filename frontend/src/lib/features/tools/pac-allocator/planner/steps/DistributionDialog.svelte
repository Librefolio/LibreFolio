<script lang="ts">
    import {onDestroy, onMount} from 'svelte';
    import {t, locale} from '$lib/i18n';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {ColumnDef, FooterCells} from '$lib/components/table/types';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {applyDistribution, distributionProposal, type DistributionRow} from '../copies';
    import {canonicalInput, sumControlPercentages} from '../decimal';
    import type {PlannerDraft} from '../draft.svelte';
    import {formatPlannerDate, formatPlannerPercentUnits} from '../format';
    import {loadCopyScope, selectableIds, type ScopeBroker} from '../scope';
    import {SourceLoad} from '../sourceLoad.svelte';
    import {BUTTON_PRIMARY, BUTTON_SECONDARY, BUTTON_WARNING, LABEL_ROW, NOTICE, TABLE, TH} from '../ui';
    import AssetNameCell from '../shared/AssetNameCell.svelte';
    import HelpTip from '../shared/HelpTip.svelte';
    import IssueList from '../shared/IssueList.svelte';
    import OwnerBrokerPicker from '../shared/OwnerBrokerPicker.svelte';
    import PlannerDialog from '../shared/PlannerDialog.svelte';
    import TableColumns from '../shared/TableColumns.svelte';
    import {withHelpCues} from '../shared/columnHelp';
    import {listIssue} from '../labels';
    import {presentSourceIssues} from '../issues';

    interface Props {
        draft: PlannerDraft;
        accountGeneration: number;
        onclose: () => void;
    }

    let {draft, accountGeneration, onclose}: Props = $props();

    const testid = 'pac-planner-distribution';
    const load = new SourceLoad();
    let scope = $state<ScopeBroker[] | null>(null);
    let scopeFailed = $state(false);
    let selected = $state<number[]>([]);
    let confirming = $state(false);
    let table = $state<DataTable<DistributionRow>>();

    const dbAssetIds = $derived(draft.data.assets.flatMap((asset) => (asset.sourceAssetId === null ? [] : [asset.sourceAssetId])));
    // No Broker ticked: a snapshot read for an earlier selection must not stay applicable.
    const proposal = $derived(load.data && selected.length > 0 ? distributionProposal(draft, load.data) : null);
    const issues = $derived(load.data && proposal ? presentSourceIssues(proposal.issues, draft, load.data).map(listIssue) : []);
    const reading = $derived(!scopeFailed && (scope === null || load.status === 'loading'));
    const maxWeight = $derived(Math.max(1, ...(proposal?.rows ?? []).map((row) => percentNumber(row.weightPercent))));
    // The backend weights of a complete distribution add up to exactly 1: the footer shows it.
    const footerCells = $derived.by((): FooterCells<DistributionRow> | undefined => {
        if (proposal?.status !== 'complete') return undefined;
        const sum = sumControlPercentages(proposal.rows.map((row) => row.weightPercent ?? '0'));
        return {
            asset: $t('tools.pacAllocator.planner.targets.total', {default: 'Total'}),
            weight: sum === null ? '—' : formatPlannerPercentUnits(sum),
        };
    });

    /** Bar length only: a picture of the weight, never a value that is sent. */
    function percentNumber(value: string | null): number {
        const canonical = canonicalInput(value ?? '');
        const number = canonical === null ? 0 : Number(canonical);
        return Number.isFinite(number) ? Math.max(0, number) : 0;
    }

    function weightHelp(): string {
        const parts = [
            $t('tools.pacAllocator.planner.distribution.denominator', {default: 'Denominator: the Assets of the scenario; cash does not enter.'}),
            $t('tools.pacAllocator.planner.distribution.differs', {default: 'If the scenario does not include all your Assets, the weights differ from the page.'}),
        ];
        if (proposal?.quantumPercent) {
            parts.push($t('tools.pacAllocator.planner.distribution.quantum', {default: 'Weights to {quantum} points; the exact sum comes from the backend.', values: {quantum: formatPlannerPercentUnits(proposal.quantumPercent)}}));
        }
        return parts.join(' ');
    }

    const columns = $derived.by((): ColumnDef<DistributionRow>[] => withHelpCues<DistributionRow>([
        {
            id: 'asset',
            header: () => $t('tools.pacAllocator.planner.routing.asset', {default: 'Asset'}),
            type: 'text',
            filterable: false,
            width: 280,
            minWidth: 180,
            getValue: (row) => row.label,
            cell: (row) => {
                const asset = draft.asset(row.assetKey);
                return {type: 'custom', component: AssetNameCell, props: {label: row.label, iconUrl: asset?.iconUrl ?? null, assetType: asset?.assetClass.toUpperCase() ?? null}};
            },
        },
        {
            id: 'bar',
            header: '',
            type: 'custom',
            sortable: false,
            filterable: false,
            width: 160,
            minWidth: 80,
            cell: (row) =>
                row.weightPercent === null
                    ? ''
                    : {
                          type: 'html',
                          html: `<div data-testid="${testid}-bar" data-asset-key="${escapeHtml(row.assetKey)}" aria-hidden="true" class="h-3 overflow-hidden rounded-full bg-gray-100 dark:bg-slate-700"><div class="h-full rounded-full bg-libre-green" style="width: ${Math.min(100, (percentNumber(row.weightPercent) / maxWeight) * 100)}%"></div></div>`,
                      },
        },
        {
            id: 'weight',
            header: () => $t('tools.pacAllocator.planner.distribution.weight', {default: 'Weight'}),
            headerTooltip: weightHelp,
            type: 'number',
            filterable: false,
            align: 'right',
            width: 120,
            minWidth: 100,
            getValue: (row) => (row.weightPercent === null ? -1 : Number(row.weightPercent)),
            cell: (row) => (row.weightPercent === null ? '—' : formatPlannerPercentUnits(row.weightPercent)),
        },
        {
            id: 'valuation',
            header: () => $t('tools.pacAllocator.planner.distribution.valuation', {default: 'Valuation'}),
            type: 'text',
            filterable: false,
            width: 260,
            minWidth: 160,
            getValue: (row) => valuation(row),
            cell: (row) => valuation(row),
        },
    ]));

    async function read(): Promise<void> {
        if (selected.length === 0) {
            load.stop();
            return;
        }
        draft.refreshAsOf();
        await load.load(
            {
                asOf: draft.data.asOf,
                targetCurrency: draft.data.valuationCurrency,
                sections: ['assets', 'current_distribution'],
                brokerIds: [...selected],
                assetIds: dbAssetIds,
                fxPairs: [],
            },
            accountGeneration,
        );
    }

    onMount(async () => {
        try {
            scope = await loadCopyScope();
        } catch {
            scopeFailed = true;
            return;
        }
        selected = selectableIds(scope);
        await read();
    });

    onDestroy(() => load.stop());

    function valuation(row: DistributionRow): string {
        if (row.manual) return $t('tools.pacAllocator.planner.distribution.manual', {default: 'manual · not in the portfolio'});
        if (!row.held) return $t('tools.pacAllocator.planner.distribution.notHeld', {default: 'not held'});
        if (row.valuation === 'MARKET_PRICE') return $t('tools.pacAllocator.planner.distribution.marketPrice', {default: 'market price {date}', values: {date: formatPlannerDate(row.referenceDate, $locale)}});
        if (row.valuation === 'LAST_TRADE_PRICE') return $t('tools.pacAllocator.planner.distribution.lastTrade', {default: 'last trade price {date}', values: {date: formatPlannerDate(row.referenceDate, $locale)}});
        return $t('tools.pacAllocator.planner.distribution.missing', {default: 'no price or rate: no weight'});
    }

    function use(): void {
        if (!proposal || proposal.status !== 'complete') return;
        if (proposal.changes.length > 0) {
            confirming = true;
            return;
        }
        applyDistribution(draft, proposal);
        onclose();
    }

    function confirmUse(): void {
        confirming = false;
        if (proposal) applyDistribution(draft, proposal);
        onclose();
    }
</script>

<PlannerDialog open title={$t('tools.pacAllocator.planner.distribution.title', {default: 'Copy current distribution'})} {testid} {onclose} maxWidth="3xl">
    <div class="space-y-3" data-testid="{testid}-body" data-state={load.status} data-status={proposal?.status ?? ''} aria-busy={reading}>
        <p class="flex items-start gap-0.5 text-sm text-gray-700 dark:text-gray-300" data-testid="{testid}-subtitle">
            <span>{$t('tools.pacAllocator.planner.distribution.subtitle', {default: 'How much each of these Assets weighs today in the ticked Brokers, counting only these Assets: together they make 100%. Cash and the other Assets you hold do not count.'})}</span>
            <HelpTip
                label={$t('tools.pacAllocator.planner.distribution.title', {default: 'Copy current distribution'})}
                help={$t('tools.pacAllocator.planner.distribution.rule', {default: 'Weights only, no portfolio value. A base to edit, not advice. A target you changed is not overwritten without confirmation.'})}
                testid="{testid}-rule"
            />
        </p>
        {#if scopeFailed}
            <div class={NOTICE.danger} role="alert" data-testid="{testid}-scope-error">{$t('tools.pacAllocator.planner.copy.scopeError', {default: 'The Broker list could not be loaded. Nothing was copied.'})}</div>
        {:else if scope !== null && selectableIds(scope).length === 0}
            <div class={NOTICE.info} data-testid="{testid}-no-owner">{$t('tools.pacAllocator.planner.copy.noOwner', {default: 'Copying needs at least one Broker you own. Enter the values by hand instead.'})}</div>
        {:else}
            {#if scope !== null}
                <div>
                    <p class={LABEL_ROW}>
                        {$t('tools.pacAllocator.planner.distribution.brokers', {default: 'Brokers (OWNER only)'})}
                        <HelpTip label={$t('tools.pacAllocator.planner.distribution.brokers', {default: 'Brokers (OWNER only)'})} help={$t('tools.pacAllocator.planner.distribution.source', {default: 'Source: portfolio engine (the values of the Allocation page).'})} />
                    </p>
                    <OwnerBrokerPicker {scope} bind:selected testid="{testid}-scope" disabled={load.status === 'loading'} onchange={() => void read()} />
                </div>
            {/if}

            {#if load.status === 'error' && load.error}
                <div class={NOTICE.danger} role="alert" data-testid="{testid}-error">{$t(load.error.key, {default: load.error.fallback})}</div>
            {:else}
                <div class="space-y-2" data-testid="{testid}-table" data-loading={reading ? 'true' : 'false'}>
                    <TableColumns {table} testid="{testid}-columns" />
                    <DataTable
                        bind:this={table}
                        data={proposal?.rows ?? []}
                        {columns}
                        getRowId={(row) => row.assetKey}
                        storageKey="pac-planner-distribution"
                        enableSelection={false}
                        selectionMode="none"
                        enableActions={false}
                        enablePagination={false}
                        enableColumnVisibility
                        enableColumnFilters={false}
                        enableContextMenu={false}
                        tableLayout="auto"
                        {footerCells}
                        isLoading={reading}
                        emptyMessage={selected.length === 0 ? $t('tools.pacAllocator.planner.ownedAssets.noBroker', {default: 'Tick at least one Broker.'}) : undefined}
                    />
                </div>
                {#if proposal?.status === 'incomplete'}
                    <div class={NOTICE.warning} data-testid="{testid}-incomplete">{$t('tools.pacAllocator.planner.distribution.incomplete', {default: 'An Asset you hold has no price or rate: no weight is published and no target changes.'})}</div>
                {:else if proposal?.status === 'no_holdings'}
                    <div class={NOTICE.info} data-testid="{testid}-no-holdings">{$t('tools.pacAllocator.planner.distribution.noHoldings', {default: 'You hold none of these Assets: no weight, no target changes.'})}</div>
                {/if}
                <IssueList items={issues} testid="{testid}-issues" />
            {/if}
        {/if}
    </div>

    {#snippet footer()}
        <button type="button" class={BUTTON_SECONDARY} data-testid="{testid}-cancel" onclick={onclose}>{$t('common.cancel', {default: 'Cancel'})}</button>
        <button type="button" class={BUTTON_PRIMARY} disabled={load.status !== 'ready' || proposal?.status !== 'complete'} data-testid="{testid}-apply" onclick={use}>
            {$t('tools.pacAllocator.planner.distribution.apply', {default: 'Use as target'})}
        </button>
    {/snippet}
</PlannerDialog>

<!-- R13.1: a two-column table (name | before → after), not a list of «name: x% → y%» lines. -->
<PlannerDialog open={confirming} title={$t('tools.pacAllocator.planner.distribution.confirmTitle', {default: 'Replace the targets you set?'})} testid="{testid}-confirm" onclose={() => (confirming = false)} maxWidth="lg" zIndex={70}>
    <p data-testid="{testid}-confirm-message">{$t('tools.pacAllocator.planner.distribution.confirmMessage', {default: 'These targets change:'})}</p>
    <div class="max-h-80 overflow-auto rounded-lg border border-gray-200 dark:border-gray-700">
        <table class="{TABLE} w-full table-fixed" data-testid="{testid}-confirm-table">
            <thead class="sticky top-0 bg-gray-50 dark:bg-gray-900">
                <tr>
                    <th scope="col" class={TH}>{$t('tools.pacAllocator.planner.routing.asset', {default: 'Asset'})}</th>
                    <th scope="col" class="{TH} w-48 text-right">{$t('tools.pacAllocator.planner.distribution.changeColumn', {default: 'Target'})}</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-gray-100 dark:divide-gray-700/60">
                {#each proposal?.changes ?? [] as change (change.assetKey)}
                    {@const asset = draft.asset(change.assetKey)}
                    <tr data-testid="{testid}-confirm-change" data-asset-key={change.assetKey}>
                        <td class="px-3 py-2 align-middle text-gray-800 dark:text-gray-200">
                            <AssetNameCell label={change.label} iconUrl={asset?.iconUrl ?? null} assetType={asset?.assetClass.toUpperCase() ?? null} />
                        </td>
                        <td class="whitespace-nowrap px-3 py-2 text-right align-middle tabular-nums text-gray-800 dark:text-gray-200">
                            <span class="text-gray-500 dark:text-gray-400" data-testid="{testid}-confirm-from">{formatPlannerPercentUnits(change.from)}</span>
                            <span class="px-1 text-gray-400" aria-hidden="true">→</span>
                            <span class="font-semibold" data-testid="{testid}-confirm-to">{formatPlannerPercentUnits(change.to)}</span>
                        </td>
                    </tr>
                {/each}
            </tbody>
        </table>
    </div>

    {#snippet footer()}
        <button type="button" class={BUTTON_SECONDARY} data-testid="{testid}-confirm-cancel" onclick={() => (confirming = false)}>{$t('common.cancel', {default: 'Cancel'})}</button>
        <button type="button" class={BUTTON_WARNING} data-testid="{testid}-confirm-apply" onclick={confirmUse}>{$t('tools.pacAllocator.planner.distribution.confirmApply', {default: 'Replace'})}</button>
    {/snippet}
</PlannerDialog>
