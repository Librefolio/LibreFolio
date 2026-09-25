<script lang="ts">
    import {onDestroy, onMount} from 'svelte';
    import {t, locale} from '$lib/i18n';
    import ConfirmModal from '$lib/components/ui/modals/ConfirmModal.svelte';
    import {applyDistribution, distributionProposal, type DistributionRow} from '../copies';
    import type {PlannerDraft} from '../draft.svelte';
    import {formatPlannerDate, formatPlannerPercentUnits} from '../format';
    import {loadCopyScope, selectableIds, type ScopeBroker} from '../scope';
    import {SourceLoad} from '../sourceLoad.svelte';
    import {BUTTON_PRIMARY, BUTTON_SECONDARY, HINT, NOTICE, TABLE, TD, TD_NUM, TH} from '../ui';
    import AgeLabel from '../shared/AgeLabel.svelte';
    import IssueList from '../shared/IssueList.svelte';
    import OwnerBrokerPicker from '../shared/OwnerBrokerPicker.svelte';
    import PlannerDialog from '../shared/PlannerDialog.svelte';
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

    const dbAssetIds = $derived(draft.data.assets.flatMap((asset) => (asset.sourceAssetId === null ? [] : [asset.sourceAssetId])));
    const proposal = $derived(load.data ? distributionProposal(draft, load.data) : null);
    const issues = $derived(load.data && proposal ? presentSourceIssues(proposal.issues, draft, load.data).map(listIssue) : []);

    async function read(): Promise<void> {
        if (selected.length === 0) {
            load.stop();
            return;
        }
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

    const changeItems = $derived(proposal?.changes.map((change) => $t('tools.pacAllocator.planner.distribution.change', {default: '{asset}: {from} → {to}', values: {asset: change.label, from: formatPlannerPercentUnits(change.from), to: formatPlannerPercentUnits(change.to)}})) ?? []);
</script>

<PlannerDialog open title={$t('tools.pacAllocator.planner.distribution.title', {default: 'Copy current distribution'})} {testid} {onclose} maxWidth="3xl">
    <div class="space-y-3" data-testid="{testid}-body" data-state={load.status} data-status={proposal?.status ?? ''} aria-busy={load.status === 'loading'}>
        <p class={HINT}>
            {$t('tools.pacAllocator.planner.distribution.source', {
                default: 'Source: portfolio engine (the values of the Allocation page) · as of {date}',
                values: {date: formatPlannerDate(draft.data.asOf, $locale)},
            })}
        </p>

        {#if scopeFailed}
            <div class={NOTICE.danger} role="alert" data-testid="{testid}-scope-error">{$t('tools.pacAllocator.planner.copy.scopeError', {default: 'The Broker list could not be loaded. Nothing was copied.'})}</div>
        {:else if scope === null}
            <p class={HINT} role="status" data-testid="{testid}-loading">{$t('common.loading', {default: 'Loading…'})}</p>
        {:else if selectableIds(scope).length === 0}
            <div class={NOTICE.info} data-testid="{testid}-no-owner">{$t('tools.pacAllocator.planner.copy.noOwner', {default: 'Copying needs at least one Broker you own. Enter the values by hand instead.'})}</div>
        {:else}
            <div>
                <p class="text-sm font-medium">{$t('tools.pacAllocator.planner.distribution.brokers', {default: 'Brokers (OWNER only)'})}</p>
                <OwnerBrokerPicker {scope} bind:selected testid="{testid}-scope" disabled={load.status === 'loading'} onchange={() => void read()} />
            </div>
        {/if}

        <p class={HINT}>{$t('tools.pacAllocator.planner.distribution.denominator', {default: 'Denominator: the Assets of the scenario; cash does not enter.'})}</p>
        <p class={HINT}>{$t('tools.pacAllocator.planner.distribution.differs', {default: 'If the scenario does not include all your Assets, the weights differ from the page.'})}</p>

        {#if load.status === 'loading'}
            <p class={HINT} role="status" data-testid="{testid}-reading">{$t('tools.pacAllocator.planner.copy.reading', {default: 'Reading the snapshot…'})}</p>
        {:else if load.status === 'error' && load.error}
            <div class={NOTICE.danger} role="alert" data-testid="{testid}-error">{$t(load.error.key, {default: load.error.fallback})}</div>
        {:else if proposal}
            <div class="overflow-x-auto">
                <table class={TABLE} data-testid="{testid}-table">
                    <thead>
                        <tr>
                            <th scope="col" class={TH}>{$t('tools.pacAllocator.planner.routing.asset', {default: 'Asset'})}</th>
                            <th scope="col" class="{TH} text-right">{$t('tools.pacAllocator.planner.distribution.weight', {default: 'Weight'})}</th>
                            <th scope="col" class={TH}>{$t('tools.pacAllocator.planner.distribution.valuation', {default: 'Valuation'})}</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100 dark:divide-gray-800">
                        {#each proposal.rows as row (row.assetKey)}
                            <tr data-testid="{testid}-row" data-asset-key={row.assetKey} data-held={row.held ? 'true' : 'false'} data-stale={row.stale ? 'true' : 'false'}>
                                <td class={TD}>{row.label}</td>
                                <td class={TD_NUM}>{row.weightPercent === null ? '—' : formatPlannerPercentUnits(row.weightPercent)}</td>
                                <td class={TD}>
                                    <span class="flex flex-wrap items-center gap-2">
                                        {valuation(row)}
                                        {#if row.held && row.referenceDate}<AgeLabel date={row.referenceDate} asOf={proposal.asOf} testid="{testid}-age" />{/if}
                                    </span>
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
            {#if proposal.quantumPercent}
                <p class={HINT}>{$t('tools.pacAllocator.planner.distribution.quantum', {default: 'Weights to {quantum} points; the exact sum comes from the backend.', values: {quantum: formatPlannerPercentUnits(proposal.quantumPercent)}})}</p>
            {/if}
            {#if proposal.status === 'incomplete'}
                <div class={NOTICE.warning} data-testid="{testid}-incomplete">{$t('tools.pacAllocator.planner.distribution.incomplete', {default: 'An Asset you hold has no price or rate: no weight is published and no target changes.'})}</div>
            {:else if proposal.status === 'no_holdings'}
                <div class={NOTICE.info} data-testid="{testid}-no-holdings">{$t('tools.pacAllocator.planner.distribution.noHoldings', {default: 'You hold none of these Assets: no weight, no target changes.'})}</div>
            {/if}
            <IssueList items={issues} testid="{testid}-issues" />
        {/if}

        <p class={HINT}>{$t('tools.pacAllocator.planner.distribution.rule', {default: 'Weights only, no portfolio value. A base to edit, not advice. A target you changed is not overwritten without confirmation.'})}</p>
    </div>

    {#snippet footer()}
        <button type="button" class={BUTTON_SECONDARY} data-testid="{testid}-cancel" onclick={onclose}>{$t('common.cancel', {default: 'Cancel'})}</button>
        <button type="button" class={BUTTON_PRIMARY} disabled={load.status !== 'ready' || proposal?.status !== 'complete'} data-testid="{testid}-apply" onclick={use}>
            {$t('tools.pacAllocator.planner.distribution.apply', {default: 'Use as target'})}
        </button>
    {/snippet}
</PlannerDialog>

<ConfirmModal
    open={confirming}
    title={$t('tools.pacAllocator.planner.distribution.confirmTitle', {default: 'Replace the targets you set?'})}
    message={$t('tools.pacAllocator.planner.distribution.confirmMessage', {default: 'These targets change:'})}
    items={changeItems}
    warning
    zIndex={70}
    testId="{testid}-confirm"
    onConfirm={confirmUse}
    onCancel={() => (confirming = false)}
/>
